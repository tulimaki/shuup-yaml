Shuup YAML
==========

Import categories, manufacturers and products to Shuup.

Shuup is an Open Source E-Commerce Platform based on Django and Python.

https://shuup.com/

Copyright
---------

Copyright (C) 2012-2018 by Shuup Inc. <support@shuup.com>

Shuup is International Registered Trademark & Property of Shuup Inc.,
Business Address: 1013 Centre Road, Suite 403-B,
Wilmington, Delaware 19805,
United States Of America

CLA
---

Contributor License Agreement is required for any contribution to this
project.  Agreement is signed as a part of pull request process.  See
the CLA.rst file distributed with Shuup.

License
-------

Shuup YAML is published under Open Software License version 3.0 (OSL-3.0).
See the LICENSE file distributed with Shuup.

Documentation
-------------

For YAML format see example data.

Running tests
-------------

You can run tests with `py.test <http://pytest.org/>`_.

Requirements for running tests:

* Your virtualenv needs to have Shuup installed.

* Project root must be in the Python path.  This can be done with:

  .. code:: sh

     pip install -e .

To run tests, use command:

.. code:: sh

   py.test -v shuup_yaml_tests
