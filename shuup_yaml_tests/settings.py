# -*- coding: utf-8 -*-
# This file is part of Shuup.
#
# Copyright (c) 2012-2018, Shuup Inc. All rights reserved.
#
# This source code is licensed under the OSL-3.0 license found in the
# LICENSE file in the root directory of this source tree.
from shuup_workbench.test_settings import *  # noqa

INSTALLED_APPS = list(locals().get('INSTALLED_APPS', [])) + [
    'shuup_yaml',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
        'TEST': {'NAME': 'test_db.sqlite3'},
    }
}
