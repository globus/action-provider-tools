
Features
--------

- Added a new configuration class ``ActionProviderConfig`` with the initial option to
  ``scrub_validation_errors`` (default: True).

  - If disabled, user-provided data may be included in library raised validation errors.

Changes
-------

- Scrubbed and non-scrubbed jsonschema errors have been enhanced. They now follow
  the format

  .. code-block:: text

    "Field '<jsonpath>' (category: '<error_category>'): Input failed schema validation

  - Sample:

    .. code-block:: text

      "Field 'data.attributes.name' (category: 'required'): Input failed schema
      validation

- Pydantic errors will similarly include a category in their error messages.
