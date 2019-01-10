# -*- coding: utf-8 -*-
# This file is part of Shuup.
#
# Copyright (c) 2012-2019, Shoop Commerce Ltd. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
import os

from django.conf import settings
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.translation import activate

from shuup.core.models import Shop, TaxClass
from shuup_yaml.importer import (
    import_categories, import_manufacturers, import_products
)


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--shop-domain', type=str, required=True, help="Shop domain")
        parser.add_argument('--data-path', type=str, required=True, help="The path of 'data' folder")
        parser.add_argument('--language', type=str, default="en", help="Language code")
        parser.add_argument('--tax-class', type=str, required=False, default=None, help="Tax Class Identifier")
        parser.add_argument('--no-dry-run', action="store_true", dest="no_dry_run", default=False, help="No dry-run")

    def handle(self, *args, **options):
        lang = options["language"]
        domain = options["shop_domain"]
        data_path = os.path.realpath(os.path.expanduser(options["data_path"]))
        no_dry_run = options["no_dry_run"]
        tax_class_identifier = options.get("tax_class")

        def run_import(include_images=True):
            available_languages = [k for k, v in settings.LANGUAGES]
            if lang not in available_languages:
                raise Exception("Invalid language provided, correct options are: %r" % available_languages)
            activate(lang)

            shop = Shop.objects.filter(domain=domain).first()
            if not shop:
                raise Exception("Invalid shop provided, please check the domain.")

            if tax_class_identifier:
                tax_class = TaxClass.objects.filter(identifier=tax_class_identifier).first()
            else:
                tax_class = TaxClass.objects.first()

            if not tax_class:
                raise Exception("Tax class doesn't exist.")

            if not os.path.exists(data_path):
                raise Exception("Path %s doesn't exist" % data_path)

            img_path = os.path.join(data_path, "images")
            if not os.path.exists(img_path):
                raise Exception("Path %s doesn't exist" % img_path)

            category_file = os.path.join(data_path, "categories.yaml")
            if os.path.isfile(category_file):
                import_categories(shop, category_file)

            manufacturer_file = os.path.join(data_path, "manufacturers.yaml")
            if os.path.isfile(manufacturer_file):
                import_manufacturers(shop, manufacturer_file, img_path)

            product_file = os.path.join(data_path, "products.yaml")
            if os.path.isfile(product_file):
                import_products(shop, product_file, img_path, tax_class, include_images)

        if no_dry_run:
            print("**** RUNNING UPDATES ****")  # noqa
            with transaction.atomic():
                run_import()
        else:
            print("**** RUNNING AS DRY-RUN ****")  # noqa
            transaction.set_autocommit(False)
            run_import(include_images=False)
