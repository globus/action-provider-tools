Changes
-------

- Error descriptions in responses are now always strings (previously they could also
  be lists of strings or lists of dictionaries).
- Input validation errors now use an HTTP response status code of 422.
- Validation errors no longer return input data in their description.
