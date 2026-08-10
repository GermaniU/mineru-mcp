"""Tools de tareas asíncronas: submit, status, result."""

from .. import gpu_arbiter, mineru_client
from ..config import MINERU_IS_EXTERNAL, MINERU_URL
from ..helpers import build_form, extract_md, format_md_response, resolve_input_file


async def submit_parse_task(
    file_path: str | None = None,
    file_base64: str | None = None,
    file_name: str | None = None,
    backend: str = "pipeline",
    effort: str = "medium",
    image_analysis: bool = False,
    parse_method: str = "auto",
    lang: str = "es",
    formula_enable: bool = True,
    table_enable: bool = True,
    start_page: int | None = None,
    end_page: int | None = None,
) -> str:
    try:
        path, is_temp = resolve_input_file(file_path, file_base64, file_name)
    except ValueError as e:
        return f"Error: {e}"

    if MINERU_IS_EXTERNAL:
        return f"BLOQUEADO por seguridad: MINERU_URL apunta a {MINERU_URL} (servidor externo)."

    gpu_err = gpu_arbiter.ensure_gpu_for_mineru(backend)
    if gpu_err:
        return f"Error liberando GPU: {gpu_err}"

    try:
        form = build_form(backend, parse_method, effort, lang, formula_enable, table_enable, image_analysis)
        if start_page is not None:
            form["start_page_id"] = str(int(start_page))
        if end_page is not None:
            form["end_page_id"] = str(int(end_page))
        data = await mineru_client.submit_task(path, form)
    except Exception as e:  # noqa: BLE001
        return f"Error: {type(e).__name__}: {e}"
    finally:
        if is_temp:
            path.unlink(missing_ok=True)
        gpu_arbiter.release_gpu_after_mineru()

    task_id = data.get("task_id") or data.get("id") or "?"
    return (f"Tarea enviada exitosamente.\ntask_id: {task_id}\narchivo: {file_name or path.name}\n"
            f"backend: {form['backend']}\n\nUsar get_task_status(task_id) para saber cuándo terminó.")


async def get_task_status(task_id: str) -> str:
    try:
        data = await mineru_client.task_status(task_id)
    except Exception as e:  # noqa: BLE001
        return f"Error: {type(e).__name__}: {e}"

    status = data.get("status", "unknown")
    progress = data.get("progress") or data.get("percentage")
    message = data.get("message") or data.get("error") or ""
    lines = [f"task_id: {task_id}", f"status: {status}"]
    if progress is not None:
        lines.append(f"progreso: {progress}%")
    if message:
        lines.append(f"mensaje: {message}")
    if status == "completed":
        lines.append("\nListo. Usar get_task_result(task_id).")
    elif status == "failed":
        lines.append("\nError en el parseo.")
    elif status in ("pending", "processing"):
        lines.append("\nEn proceso.")
    return "\n".join(lines)


async def get_task_result(task_id: str) -> str:
    try:
        status_data = await mineru_client.task_status(task_id)
        if status_data.get("status") != "completed":
            return (f"La tarea {task_id} aún no está completada "
                    f"(estado: {status_data.get('status', 'unknown')}).")
        data = await mineru_client.task_result(task_id)
    except Exception as e:  # noqa: BLE001
        return f"Error: {type(e).__name__}: {e}"

    md = extract_md(data, task_id)
    if not md.strip():
        return f"La tarea {task_id} completó pero no devolvió contenido."
    filename = data.get("filename") or task_id
    meta = {"pages": data.get("pages") or data.get("total_pages"), "backend": data.get("backend")}
    return format_md_response(md, filename, meta)
