import uvicorn
from dataclasses import dataclass

from fastcore.utils import *
from fastcore.xml import *

from fasthtml import FastHTML

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
        link = A(self.title, href='#',
                hx_get=f'/todos/{self.id}', hx_target="#current-todo")
        return Li(link, id=f'todo-{self.id}')

TODO_LIST: list[TodoItem] = [
    TodoItem(id=0, title="Start writing todo list", done=True),
    TodoItem(id=1, title="???", done=False),
    TodoItem(id=2, title="Profit", done=False),
]

htmxscr = Script(
    src="https://unpkg.com/htmx.org@1.9.12", crossorigin="anonymous",
    integrity="sha384-ujb1lZYygJmzgSwoxRggbCHcjc0rB2XoQrxeTUQyRjrOnlCoYta87iKBWq3EsdM2")
picocss = Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/@picocss/pico@latest/css/pico.min.css")

"""
@app.put("/{item_id}")
async def update_item(request):
    data = await request.json()
    item_id = request.path_params['item_id']
    todo_item = find_todo(item_id)
    todo_item.title = data['title']
    todo_item.done = data['done']
    return RedirectResponse("/", status_code=303)
"""

# debug=True, routes=rt.routes, exception_handlers=exception_handlers
app = FastHTML()

@app.get("/favicon.ico")
async def favicon(request): return FileResponse('favicon.ico', media_type='image/x-icon')

@app.post("/")
async def add_item(todo:TodoItem):
    todo.id = len(TODO_LIST)+1
    TODO_LIST.append(todo)
    return todo, mk_input(hx_swap_oob='true')

def find_todo(tid):
    try: return next(o for o in TODO_LIST if o.id==tid)
    except: raise NotFoundException() from None

@app.delete("/todos/{tid}")
async def del_todo(tid:int):
    TODO_LIST.remove(find_todo(tid))
    return Div(hx_swap_oob='true', id='todo-details')

@app.get("/todos/{tid}")
async def get_todo_by_id(tid:int):
    todo = find_todo(tid)
    btn = Button('delete', hx_delete=f'/todos/{todo.id}',
                 hx_target=f"#todo-{todo.id}", hx_swap="outerHTML")
    return Div(Div(todo.title), btn, id='todo-details')

def mk_input(**kw): return Input(type="text", name="title", placeholder="New Todo", id="new-todo-title", **kw)

@app.get("/")
async def get_todos(req):
    form = Form(mk_input(), Button("Add Todo", type="submit"), method="post",
                hx_post="/", hx_target="#todo-list", hx_swap="beforeend", id="new-todo-form",)
    todo_ul = Ul(*TODO_LIST, id="todo-list")
    return Html(
        Head(Title('TODO list'), htmxscr, picocss),
        Body(Main(H1('Todo list'), form, todo_ul, Div(id='current-todo'), cls='container'))
    )
