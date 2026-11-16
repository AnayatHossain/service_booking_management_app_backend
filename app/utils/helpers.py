from bson import ObjectId
from typing import Any, Dict, List


def format_mongo_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Mongo document ObjectId to string id and remove internal fields."""
    if not doc:
        return {}
    formatted = dict(doc)
    if "_id" in formatted:
        formatted["id"] = str(formatted.pop("_id"))
    # Also format any nested ObjectIds if present
    for k, v in list(formatted.items()):
        if isinstance(v, ObjectId):
            formatted[k] = str(v)
    return formatted


def format_mongo_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [format_mongo_doc(d) for d in docs]
