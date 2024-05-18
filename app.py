import uvicorn
from dataclasses import dataclass

from starlette.responses import FileResponse, RedirectResponse, JSONResponse, HTMLResponse
from fastcore.utils import *
from fastcore.xml import *
from fasthtml import *

"""
class NotFoundException(HTTPException):
    def __init__(self): return super().__init__(404)

async def not_found(request: Request, exc: NotFoundException):
    return HTMLResponse(content='not found', status_code=exc.status_code)

exception_handlers = { NotFoundException: not_found }

rt = Router(headtags=[htmxscr, picocss])

def wrap_root(resp, headtags):
    title = Title('Page')
    if isinstance(resp, tuple): title,resp = resp
    return Html(Head(title, *headtags), resp)
"""

@dataclass
class TodoItem:
    title: str; id: int = -1; done: bool = False
    def __xt__(self):
        show = A(self.title, href='#',
                hx_get=f'/todos/{self.id}', hx_target="#current-todo")
        edit = A('edit', href='#',
                hx_get=f'/edit/{self.id}', hx_target="#current-todo")
        dt = ' (done)' if self.done else ''
        return Li(show, dt, ' | ', edit, id=f'todo-{self.id}')

TODO_LIST = [
    TodoItem(id=0, title="Start writing todo list", done=True),
    TodoItem(id=1, title="???", done=False),
    TodoItem(id=2, title="Profit", done=False),
]

htmxscr = Script(
    src="https://unpkg.com/htmx.org@1.9.12", crossorigin="anonymous",
    integrity="sha384-ujb1lZYygJmzgSwoxRggbCHcjc0rB2XoQrxeTUQyRjrOnlCoYta87iKBWq3EsdM2")
picocss = Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/@picocss/pico@latest/css/pico.min.css")
mycss   = Link(rel="stylesheet", href="picovars.css")

# debug=True, exception_handlers=exception_handlers
app = FastHTML()

reg_re_param("static", "ico|gif|jpg|jpeg|webm|css|js")

@app.get("/{fname:path}.{ext:static}")
async def image(fname:str, ext:str): return FileResponse(f'{fname}.{ext}')

@app.get("/static/{fname:path}")
async def static(fname:str): return FileResponse(f'static/{fname}')

@app.post("/")
async def add_item(todo:TodoItem):
    todo.id = len(TODO_LIST)+1
    TODO_LIST.append(todo)
    return todo, mk_input(hx_swap_oob='true')

def find_todo(id):
    try: return next(o for o in TODO_LIST if o.id==id)
    except: raise NotFoundException(f'Todo #{id}') from None

def clr_details(): return Div(hx_swap_oob='innerHTML', id='current-todo')

@app.get("/edit/{id}")
async def edit_item(id:int):
    form = Form(Fieldset(Input(id="title"), Button("Save"), role="group"),
                Hidden(id="id"), Checkbox(id="done", label='Done'),
                hx_put="/", hx_target=f"#todo-{id}", id="edit")
    return fill_form(Article(form), find_todo(id))

@app.put("/")
async def update(todo: TodoItem):
    fill_dataclass(todo, find_todo(todo.id))
    return todo, clr_details()

@app.delete("/todos/{id}")
async def del_todo(id:int):
    TODO_LIST.remove(find_todo(id))
    return clr_details()

@app.get("/todos/{id}")
async def get_todo_by_id(id:int):
    todo = find_todo(id)
    btn = Button('delete', hx_delete=f'/todos/{todo.id}',
                 hx_target=f"#todo-{todo.id}", hx_swap="outerHTML")
    return Div(Div(todo.title), btn, id='details')

def mk_input(**kw): return Input(type="text", name="title", placeholder="New Todo", id="new-title", **kw)

@app.get("/")
async def get_todos(req):
    form = Form(Fieldset(mk_input(), Button("Add"), role="group"),
                method="post", id="new-todo",
                hx_post="/", hx_target="#todo-list", hx_swap="beforeend")
    todo_ul = Ul(*TODO_LIST, id="todo-list")
    return Html(
        Head(Title('TODO list'), htmxscr, picocss, mycss),
        Body(Main(H1('Todo list'), form, todo_ul, Div(id='current-todo'),
                  cls='container'), style="max-width: 60rem; margin: 0 auto;"))
