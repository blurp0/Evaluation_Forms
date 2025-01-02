def linear_search(objects, search_query, *attributes):
    """
    Perform a linear search on a list of objects based on the given attributes.

    :param objects: List of objects to search through
    :param search_query: Search query (can be partial or full name, string)
    :param attributes: Attributes of the object to compare with search query (e.g., 'first_name', 'last_name', 'title', 'email')
    :return: List of objects that match the search query
    """
    search_parts = search_query.lower().split()  # Split the search query into parts and make it lowercase
    result = []

    for obj in objects:
        # Extract the attributes dynamically (e.g., first_name, last_name, title, etc.)
        values = [getattr(obj, attr, "").lower() if getattr(obj, attr, None) else "" for attr in attributes]

        matched = False

        # Case when the search query has only one part (e.g., "Miguel")
        if len(search_parts) == 1:
            if any(part in value for value in values for part in search_parts):
                matched = True

        # Case when the search query has two parts (e.g., "John" and "Miguel")
        elif len(search_parts) == 2:
            first_query, second_query = search_parts
            if len(values) >= 2 and any(
                    first_query in values[0] and second_query in values[1] for values in zip(values, values[1:])):
                matched = True

        # If the item matches the search query, add it to the result list
        if matched:
            result.append(obj)

    return result
