# -*- coding: utf-8 -*-
# This file is part of Shuup.
#
# Copyright (c) 2012-2018, Shuup Inc. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
import os

import pytest
from django.core import management

from shuup.core.models import Category, Manufacturer, Product, ProductMedia
from shuup.testing import factories


@pytest.mark.django_db
def test_import():
    factories.get_default_product_type()
    factories.get_default_sales_unit()
    tax_class = factories.get_default_tax_class()

    shop = factories.get_default_shop()
    shop_domain = "test"
    shop.domain = shop_domain
    shop.save()

    supplier = factories.get_default_supplier()
    supplier.shops = [shop]

    assert shop.domain == shop_domain

    args = [
        "--shop-domain", shop_domain,
        "--data-path", os.path.join(os.path.dirname(__file__), "..", "data"),
        "--language", "en",
        "--tax-class", tax_class.identifier,
        "--no-dry-run"
    ]
    management.call_command("import_yaml", *args, **{})

    assert Category.objects.count() == 18
    assert Manufacturer.objects.count() == 71
    assert Product.objects.count() == 143
    assert Product.objects.filter(shop_products__shop=shop).count() == 143

    _test_product(shop, "08712942000P", "Dog Supplies", ["Dog Food"], "Pedigree")
    _test_product(shop, "029W002479034000", "Dog Supplies", ["Dog Collars, Harnesses and Leashes"], "Champion Breed")
    _test_product(shop, "SPM9885958922", "Cat Supplies", ["Litter Boxes and Accessories"], "Trixie Pet Products")

    assert ProductMedia.objects.filter(shops=shop).count() == Product.objects.count()


def _test_product(shop, sku, primary_category, additional_categories, manufacturer):
    product = Product.objects.filter(sku=sku).first()
    assert product
    shop_product = product.get_shop_instance(shop)
    assert shop_product
    assert shop_product.primary_category.identifier == primary_category
    additional_category_identifiers = [cat.identifier for cat in shop_product.categories.all()]
    assert primary_category in additional_category_identifiers
    for category_identifier in additional_categories:
        assert category_identifier in additional_category_identifiers

    if manufacturer:
        assert product.manufacturer.identifier == manufacturer
        assert product.manufacturer.name != ""
