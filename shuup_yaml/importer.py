# -*- coding: utf-8 -*-
# This file is part of Shuup.
#
# Copyright (c) 2012-2018, Shuup Inc. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
from __future__ import unicode_literals

import os
from collections import defaultdict

import six
import yaml
from django.utils.text import slugify

from shuup.core.models import (
    Category, CategoryStatus, CategoryVisibility, Manufacturer, Product,
    ProductMedia, ProductMediaKind, ProductType, SalesUnit, ShopProduct,
    Supplier
)
from shuup.utils.filer import filer_image_from_data
from shuup.utils.numbers import parse_decimal_string


def create_from_datum(model, identifier, content, i18n_fields=(), identifier_field="identifier"):
    """
    Create or update an object from a flat datum.

    :param model: Model class
    :param identifier: Object identifier
    :type identifier: str
    :param content: Map of data
    :type content: dict
    :param i18n_fields: List of fields that should be interpreted as i18n
    :type i18n_fields: Iterable[str]
    :param identifier_field: Model field for identifier
    :type identifier_field: str
    :return: Saved model
    """
    content = content.copy()
    if content.get("ignored"):
        return None
    i18n_data = defaultdict(dict)
    normal_data = {}

    # Gather i18n-declared data from the object
    for field in i18n_fields:
        for lang_code, value in content.pop(field, {}).items():
            i18n_data[lang_code][field] = value

    # Gather non-i18n-declared data from the object
    for field, value in content.items():
        if isinstance(value, (int, float, bool)) or isinstance(value, six.string_types):
            if isinstance(value, six.binary_type):
                value = value.decode("UTF-8")
            normal_data[field] = value

    # Retrieve or initialize object
    kwargs = {identifier_field: identifier}
    object = (model.objects.filter(**kwargs).first() or model(**kwargs))
    # Set non-i18n fields
    for field, value in normal_data.items():
        setattr(object, field, value)

    # Set i18n fields
    for lang_code, data in i18n_data.items():
        object.set_current_language(lang_code)
        for field, value in data.items():
            setattr(object, field, value)

    return object


def get_category_identifier_for_shop(shop, category_identifier):
    return "%s-%s" % (shop.id, slugify(category_identifier))


def get_manufacturer_identifier_for_shop(shop, manufacturer_identifier):
    return "%s-%s" % (shop.id, slugify(manufacturer_identifier))


class ProductImporter(object):
    i18n_props = {"name", "description"}

    def __init__(self, shop, image_dir, tax_class, include_images):
        self.image_dir = image_dir
        self.shop = shop
        self.sales_unit = SalesUnit.objects.first()
        self.supplier = Supplier.objects.filter(shops__id=shop.id).first()
        self.tax_class = tax_class
        self.product_type = ProductType.objects.first()
        self.include_images = include_images

    def _attach_image_from_name(self, product, image_name, shop_product):
        image_file = os.path.join(self.image_dir, image_name)
        if not os.path.isfile(image_file):
            print("Image file does not exist: %s" % image_file)  # noqa
            return

        with open(image_file, "rb") as fp:
            data = fp.read()
        filer_file = filer_image_from_data(None, "Products", image_name.split("/")[-1], data, sha1=True)
        assert filer_file
        image, _ = ProductMedia.objects.get_or_create(product=product, file=filer_file, kind=ProductMediaKind.IMAGE)
        image.shops.add(self.shop)
        product.primary_image = image
        shop_product.shop_primary_image = image

    def _attach_category(self, product, shop_product, category_identifier, as_primary_category=False):
        category = Category.objects.filter(
            identifier=get_category_identifier_for_shop(shop_product.shop, category_identifier)).first()
        if not category:
            print("Category with identifier %r does not exist" % category_identifier)  # noqa
            return

        if as_primary_category:
            product.category = category
            shop_product.primary_category = category
        shop_product.categories.add(category)

    def _attach_manufacturer(self, product, shop, manufacturer_identifier):
        manufacturer = Manufacturer.objects.filter(
            identifier=get_manufacturer_identifier_for_shop(shop, manufacturer_identifier)).first()
        if not manufacturer:
            print("Manufacturer with identifier %r does not exist" % manufacturer_identifier)  # noqa
            return
        product.manufacturer = manufacturer

    def _import_product(self, sku, data):
        product = create_from_datum(Product, sku, data, self.i18n_props, identifier_field="sku")
        price = parse_decimal_string(data.get("price", "0.00"))
        if not product:
            return
        assert isinstance(product, Product)
        product.type = self.product_type
        product.tax_class = self.tax_class
        product.sales_unit = self.sales_unit

        product.full_clean()
        product.save()
        try:
            shop_product = product.get_shop_instance(self.shop)
        except ShopProduct.DoesNotExist:
            shop_product = ShopProduct.objects.create(product=product, shop=self.shop, default_price_value=price)

        shop_product.suppliers.add(self.supplier)
        for limiter_name in ("limit_shipping_methods", "limit_payment_methods"):
            limiter_val = data.get(limiter_name, ())
            m2m_field = getattr(shop_product, limiter_name.replace("limit_", ""))
            if limiter_val:
                setattr(shop_product, limiter_name, True)

                for identifier in limiter_val:
                    m2m_field.add(m2m_field.model.objects.get(identifier=identifier))
            else:
                setattr(shop_product, limiter_name, False)
                m2m_field.clear()

        image_name = data.get("image")
        if image_name and self.include_images:
            self._attach_image_from_name(product, image_name, shop_product)

        category_identifier = data.get("category_identifier")
        if category_identifier:
            self._attach_category(product, shop_product, category_identifier, as_primary_category=True)

        additional_category_identifier = data.get("additional_category_identifier")
        if additional_category_identifier:
            self._attach_category(product, shop_product, additional_category_identifier)

        additional_category_identifiers = data.get("additional_category_identifiers")
        if additional_category_identifiers:
            for additional_category_identifier in additional_category_identifiers.split(","):
                self._attach_category(product, shop_product, additional_category_identifier)

        manufacturer_identifier = data.get("manufacturer_identifier")
        if manufacturer_identifier:
            self._attach_manufacturer(product, self.shop, manufacturer_identifier)

        shop_product.save()
        product.save()

    def import_products(self, yaml_file):
        print("Loading product")  # noqa
        with open(yaml_file, "rb") as fp:
            products = yaml.load(fp)

        print("Products loading, starting import...")  # noqa
        for sku, data in products.items():
            data["identifier_field"] = "sku"  # maybe?
            self._import_product(sku, data)


def ensure_slugged_value(data, key="slug"):
    if key not in data:
        slugdata = {}
        for lang, value in six.iteritems(data["name"]):
            slugdata[lang] = slugify(value)
        data[key] = slugdata
    return data


def import_categories(shop, yaml_file):
    print("Loading categories")  # noqa
    with open(yaml_file, "rb") as fp:
        categories = yaml.safe_load(fp)

    print("Categories loading, starting import...")  # noqa

    i18n_props = {"name", "description"}

    for category_identifier, data in sorted(categories.items()):
        ensure_slugged_value(data, "slug")
        identifier = get_category_identifier_for_shop(shop, category_identifier)
        category = create_from_datum(Category, identifier, data, i18n_props)
        category.status = CategoryStatus.VISIBLE
        category.visibility = CategoryVisibility.VISIBLE_TO_ALL
        category.save()
        category.shops.add(shop)

    Category.objects.rebuild()


def import_manufacturers(shop, yaml_file, image_dir):
    print("Loading manufacturers")  # noqa
    with open(yaml_file, "rb") as fp:
        manufacturers = yaml.safe_load(fp)

    print("Manufacturers loading, starting import...")  # noqa

    for manufacturer_identifier, data_src in sorted(manufacturers.items()):
        image_name = data_src.pop("logo", None)
        identifier = get_manufacturer_identifier_for_shop(shop, manufacturer_identifier)
        manufacturer = create_from_datum(Manufacturer, identifier, data_src)
        manufacturer.save()
        manufacturer.shops.add(shop)

        if image_name:
            image_file = os.path.join(image_dir, image_name)
            if not os.path.isfile(image_file):
                print("Image file does not exist: %s" % image_file)  # noqa
                return

            with open(image_file, "rb") as fp:
                data = fp.read()

            manufacturer.logo = filer_image_from_data(None, "Manufacturers", image_name.split("/")[-1], data, sha1=True)
            manufacturer.save()


def import_products(shop, yaml_file, image_dir, tax_class, include_images=True):
    ProductImporter(shop, image_dir, tax_class, include_images).import_products(yaml_file)
