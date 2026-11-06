
import io
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from PIL import Image

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import SellerProfile
from sellers.models import Vehicle, VehicleImage


User = get_user_model()


class VehicleImageUploadAPITests(APITestCase):

    def setUp(self):
        # Isolated media directory for every test
        self.media_temp = tempfile.TemporaryDirectory()
        media_override = override_settings(
            MEDIA_ROOT=self.media_temp.name
        )
        media_override.enable()

        self.addCleanup(media_override.disable)
        self.addCleanup(self.media_temp.cleanup)

        # Create approved seller account
        self.user = User.objects.create_user(
            username="image_dealer",
            email="image_dealer@example.com",
            password="test-password",
            role=User.Role.SELLER,
        )

        self.seller = SellerProfile.objects.create(
            user=self.user,
            store_name="Test Motors",
            store_slug="test-motors",
            status="APPROVED",
        )

        # Create vehicle
        self.vehicle = Vehicle.objects.create(
            seller=self.seller,
            make="Toyota",
            model="Corolla",
            year=2020,
            price=25000000,
            currency="MMK",
            mileage_km=50000,
            condition="USED",
            transmission="AUTOMATIC",
            fuel_type="PETROL",
            description="Test vehicle",
        )

        self.client.force_authenticate(user=self.user)

        self.upload_url = reverse(
            "vehicle-image-upload",
            kwargs={"vehicle_id": self.vehicle.id},
        )

    # --------------------------------------------------
    # IMAGE FACTORY
    # --------------------------------------------------

    def create_image_file(
        self,
        image_format="JPEG",
        filename=None,
        size=(100, 100),
    ):
        image_buffer = io.BytesIO()

        image = Image.new(
            "RGB",
            size,
            color=(40, 120, 200),
        )

        image.save(
            image_buffer,
            format=image_format,
        )

        image_buffer.seek(0)

        extension = {
            "JPEG": "jpg",
            "PNG": "png",
            "WEBP": "webp",
        }.get(image_format, "jpg")

        if filename is None:
            filename = f"test_image.{extension}"

        content_type = {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "WEBP": "image/webp",
        }.get(image_format, "application/octet-stream")

        return SimpleUploadedFile(
            filename,
            image_buffer.read(),
            content_type=content_type,
        )

    def upload_image(
        self,
        image_file,
        is_primary=None,
        position=0,
    ):
        data = {
            "image": image_file,
            "position": position,
            "alt_text": "Test vehicle image",
        }

        if is_primary is not None:
            data["is_primary"] = is_primary

        return self.client.post(
            self.upload_url,
            data,
            format="multipart",
        )

    def create_saved_image(
        self,
        filename="saved_image.jpg",
        is_primary=False,
        position=0,
    ):
        return VehicleImage.objects.create(
            vehicle=self.vehicle,
            image=self.create_image_file(
                "JPEG",
                filename=filename,
            ),
            alt_text="Saved test image",
            is_primary=is_primary,
            position=position,
        )

    # --------------------------------------------------
    # UPLOAD TESTS
    # --------------------------------------------------

    def test_jpeg_image_upload(self):
        response = self.upload_image(
            self.create_image_file("JPEG")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_png_image_upload(self):
        response = self.upload_image(
            self.create_image_file(
                "PNG",
                filename="test_image.png",
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_webp_image_upload(self):
        try:
            image_file = self.create_image_file(
                "WEBP",
                filename="test_image.webp",
            )
        except (OSError, ValueError):
            self.skipTest(
                "Current Pillow installation does not support WEBP encoding."
            )

        response = self.upload_image(image_file)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_first_uploaded_image_becomes_primary(self):
        response = self.upload_image(
            self.create_image_file("JPEG")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        image = VehicleImage.objects.get(
            vehicle=self.vehicle
        )

        self.assertTrue(image.is_primary)

    def test_new_primary_image_replaces_old_primary(self):
        first_response = self.upload_image(
            self.create_image_file("JPEG")
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        first_image = VehicleImage.objects.get(
            vehicle=self.vehicle
        )

        second_response = self.upload_image(
            self.create_image_file(
                "PNG",
                filename="second_image.png",
            ),
            is_primary="true",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )

        first_image.refresh_from_db()

        second_image = VehicleImage.objects.get(
            pk=second_response.data["id"]
        )

        self.assertFalse(first_image.is_primary)
        self.assertTrue(second_image.is_primary)

        self.assertEqual(
            self.vehicle.images.filter(
                is_primary=True
            ).count(),
            1,
        )

    def test_invalid_image_is_rejected(self):
        invalid_file = SimpleUploadedFile(
            "invalid.jpg",
            b"This is not a real image file.",
            content_type="image/jpeg",
        )

        response = self.upload_image(invalid_file)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            VehicleImage.objects.filter(
                vehicle=self.vehicle
            ).count(),
            0,
        )

    def test_image_over_5mb_is_rejected(self):
        oversized_file = SimpleUploadedFile(
            "oversized.jpg",
            b"x" * (5 * 1024 * 1024 + 1),
            content_type="image/jpeg",
        )

        response = self.upload_image(oversized_file)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            VehicleImage.objects.filter(
                vehicle=self.vehicle
            ).count(),
            0,
        )

    def test_other_seller_cannot_upload_vehicle_image(self):
        other_user = User.objects.create_user(
            username="other_image_dealer",
            email="other_image_dealer@example.com",
            password="test-password",
            role=User.Role.SELLER,
        )

        SellerProfile.objects.create(
            user=other_user,
            store_name="Other Motors",
            store_slug="other-motors",
            status="APPROVED",
        )

        self.client.force_authenticate(
            user=other_user
        )

        response = self.upload_image(
            self.create_image_file("JPEG")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        self.assertEqual(
            VehicleImage.objects.filter(
                vehicle=self.vehicle
            ).count(),
            0,
        )

    # --------------------------------------------------
    # DELETE IMAGE TESTS
    # --------------------------------------------------

    def test_seller_can_delete_own_image(self):
        image = self.create_saved_image(
            is_primary=True
        )

        url = reverse(
            "vehicle-image-delete",
            kwargs={"image_id": image.id},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            VehicleImage.objects.filter(
                pk=image.id
            ).exists()
        )

    def test_deleting_primary_promotes_next_image(self):
        first_image = self.create_saved_image(
            filename="first.jpg",
            is_primary=True,
            position=0,
        )

        second_image = self.create_saved_image(
            filename="second.jpg",
            position=1,
        )

        url = reverse(
            "vehicle-image-delete",
            kwargs={"image_id": first_image.id},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        second_image.refresh_from_db()

        self.assertTrue(second_image.is_primary)

        self.assertEqual(
            self.vehicle.images.filter(
                is_primary=True
            ).count(),
            1,
        )

    # --------------------------------------------------
    # PRIMARY IMAGE TESTS
    # --------------------------------------------------

    def test_seller_can_change_primary_image(self):
        first_image = self.create_saved_image(
            filename="first.jpg",
            is_primary=True,
            position=0,
        )

        second_image = self.create_saved_image(
            filename="second.jpg",
            position=1,
        )

        url = reverse(
            "vehicle-image-primary",
            kwargs={"image_id": second_image.id},
        )

        response = self.client.patch(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        first_image.refresh_from_db()
        second_image.refresh_from_db()

        self.assertFalse(first_image.is_primary)
        self.assertTrue(second_image.is_primary)

        self.assertEqual(
            self.vehicle.images.filter(
                is_primary=True
            ).count(),
            1,
        )

    # --------------------------------------------------
    # IMAGE REORDER TESTS
    # --------------------------------------------------

    def test_seller_can_reorder_vehicle_images(self):
        first_image = self.create_saved_image(
            filename="first.jpg",
            position=0,
        )

        second_image = self.create_saved_image(
            filename="second.jpg",
            position=1,
        )

        third_image = self.create_saved_image(
            filename="third.jpg",
            position=2,
        )

        url = reverse(
            "vehicle-image-reorder",
            kwargs={"vehicle_id": self.vehicle.id},
        )

        response = self.client.patch(
            url,
            {
                "image_ids": [
                    third_image.id,
                    first_image.id,
                    second_image.id,
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        first_image.refresh_from_db()
        second_image.refresh_from_db()
        third_image.refresh_from_db()

        self.assertEqual(third_image.position, 0)
        self.assertEqual(first_image.position, 1)
        self.assertEqual(second_image.position, 2)

    def test_reorder_rejects_missing_image_ids(self):
        first_image = self.create_saved_image(
            filename="first.jpg",
            position=0,
        )

        self.create_saved_image(
            filename="second.jpg",
            position=1,
        )

        url = reverse(
            "vehicle-image-reorder",
            kwargs={"vehicle_id": self.vehicle.id},
        )

        response = self.client.patch(
            url,
            {
                "image_ids": [first_image.id]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_reorder_rejects_duplicate_image_ids(self):
        first_image = self.create_saved_image(
            filename="first.jpg",
            position=0,
        )

        second_image = self.create_saved_image(
            filename="second.jpg",
            position=1,
        )

        url = reverse(
            "vehicle-image-reorder",
            kwargs={"vehicle_id": self.vehicle.id},
        )

        response = self.client.patch(
            url,
            {
                "image_ids": [
                    first_image.id,
                    second_image.id,
                    first_image.id,
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
