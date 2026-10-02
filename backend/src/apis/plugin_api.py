"""
Plugin Registry REST API

Endpoints for registering, activating, and managing NexusAI plugins.
"""

from typing import Optional
from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from src.services.plugins.plugin_service import PluginService

router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])

_service: Optional[PluginService] = None


def configure(service: PluginService):
    global _service
    _service = service


def _check():
    if not _service:
        raise HTTPException(status_code=503, detail="Plugin service not initialized")


@router.get("")
async def list_plugins():
    _check()
    return {"plugins": _service.list_plugins(), "total": len(_service.list_plugins())}


@router.get("/{plugin_id}")
async def get_plugin(plugin_id: str):
    _check()
    record = _service.get_plugin(plugin_id)
    if not record:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {
        "id": record.id,
        "manifest": record.manifest.model_dump(),
        "status": record.status.value,
        "tools": [t.model_dump() for t in record.tools],
        "journeys": [j.model_dump() for j in record.journeys],
        "registered_at": record.registered_at.isoformat(),
        "activated_at": record.activated_at.isoformat() if record.activated_at else None,
    }


@router.post("/register")
async def register_plugin(file: Optional[UploadFile] = File(None), manifest: Optional[dict] = None):
    _check()
    try:
        if file:
            content = await file.read()
            if file.filename and file.filename.endswith(".zip"):
                record = _service.register_from_zip(content)
            else:
                import json
                manifest_dict = json.loads(content)
                record = _service.register_from_dict(manifest_dict)
        elif manifest:
            record = _service.register_from_dict(manifest)
        else:
            raise HTTPException(status_code=400, detail="Provide a file (zip or JSON) or manifest body")

        return {
            "success": True,
            "plugin_id": record.id,
            "name": record.manifest.name,
            "tools": len(record.tools),
            "journeys": len(record.journeys),
            "status": record.status.value,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Plugin registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register/json")
async def register_plugin_json(body: dict):
    """Register a plugin from a JSON body with manifest, tools, and journeys."""
    _check()
    try:
        manifest = body.get("manifest", body)
        tools = body.get("tools", [])
        journeys = body.get("journeys", [])
        record = _service.register_from_dict(manifest, tools, journeys)
        return {
            "success": True, "plugin_id": record.id, "name": record.manifest.name,
            "tools": len(record.tools), "journeys": len(record.journeys), "status": record.status.value,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{plugin_id}/activate")
async def activate_plugin(plugin_id: str):
    _check()
    try:
        record = _service.activate(plugin_id)
        return {"success": True, "plugin_id": record.id, "status": record.status.value,
                "tools_registered": len(record.tools)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{plugin_id}/deactivate")
async def deactivate_plugin(plugin_id: str):
    _check()
    try:
        record = _service.deactivate(plugin_id)
        return {"success": True, "plugin_id": record.id, "status": record.status.value}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{plugin_id}")
async def delete_plugin(plugin_id: str):
    _check()
    if _service.delete(plugin_id):
        return {"success": True, "deleted": plugin_id}
    raise HTTPException(status_code=404, detail="Plugin not found")


@router.get("/{plugin_id}/tools")
async def list_plugin_tools(plugin_id: str):
    _check()
    record = _service.get_plugin(plugin_id)
    if not record:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {"tools": [t.model_dump() for t in record.tools]}


@router.get("/{plugin_id}/journeys")
async def list_plugin_journeys(plugin_id: str):
    _check()
    record = _service.get_plugin(plugin_id)
    if not record:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return {"journeys": [j.model_dump() for j in record.journeys]}
