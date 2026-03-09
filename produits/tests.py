from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Category, Produit, StockMovement


class ImportProduitsTests(TestCase):
    def test_import_creates_products_and_stock_movement(self):
        csv_content = (
            "nom;prix;quantite;stock_min;fournisseur;categorie\n"
            "Souris USB;5000;12;3;Fournisseur A;Accessoires\n"
        )
        fichier = SimpleUploadedFile(
            "produits.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(reverse("import_produits"), {"fichier_produits": fichier})

        self.assertEqual(response.status_code, 302)
        produit = Produit.objects.get(nom="Souris USB")
        self.assertEqual(produit.prix, Decimal("5000"))
        self.assertEqual(produit.quantite, 12)
        self.assertEqual(produit.stock_min, 3)
        self.assertEqual(produit.fournisseur.nom, "Fournisseur A")
        self.assertEqual(produit.category.nom, "Accessoires")
        self.assertTrue(produit.qr_code)

        mouvement = StockMovement.objects.get(produit=produit)
        self.assertEqual(mouvement.type_mouvement, "entree")
        self.assertEqual(mouvement.stock_avant, 0)
        self.assertEqual(mouvement.stock_apres, 12)

    def test_import_updates_existing_product(self):
        category = Category.objects.create(nom="Informatique")
        produit = Produit.objects.create(
            nom="Clavier",
            prix=Decimal("10000"),
            quantite=5,
            stock_min=1,
            category=category,
        )

        csv_content = (
            "nom;prix;quantite;stock_min;categorie\n"
            "Clavier;12000;9;2;Informatique\n"
        )
        fichier = SimpleUploadedFile(
            "maj_produits.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(reverse("import_produits"), {"fichier_produits": fichier})

        self.assertEqual(response.status_code, 302)
        produit.refresh_from_db()
        self.assertEqual(produit.prix, Decimal("12000"))
        self.assertEqual(produit.quantite, 9)
        self.assertEqual(produit.stock_min, 2)

        mouvements = StockMovement.objects.filter(produit=produit).order_by("id")
        self.assertEqual(mouvements.count(), 1)
        self.assertEqual(mouvements.first().type_mouvement, "ajustement")
        self.assertEqual(mouvements.first().stock_avant, 5)
        self.assertEqual(mouvements.first().stock_apres, 9)
