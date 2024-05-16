import uvicorn, socket, time

from dataclasses import dataclass
from httpx import get,post
from IPython import display
from functools import wraps

from fastcore.utils import *
from fastcore.xml import *

from starlette.applications import Starlette
from starlette.routing import Route, Mount, WebSocketRoute
from starlette.responses import Response, HTMLResponse, RedirectResponse, FileResponse
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

@dataclass
class TodoItem:
    id: int; title: str; done: bool
    def __xt__(self):
        before = "console.log('Making a request!')"
        after = "console.log('Done making a request!')"
        link = A(self.title, href='#',
                hx_get=f'/todos/{self.id}', hx_target="#current-todo",
                hx_on__after_request=after, hx_on__before_request=before)
        return Li(link, id=f'todo-{self.id}')

TODO_LIST: list[TodoItem] = [
    TodoItem("0", title="Start writing TODO list", done=True),
    TodoItem("1", title="???", done=False),
    TodoItem("2", title="Profit", done=False),
]

def wrap_root(resp, headtags):
    title = Title('Page')
    if isinstance(resp, tuple): title,resp = resp
    return Html(Head(title, *headtags), resp)

class Router:
    def __init__(self, headtags=None, routes=None):
        self.rt = routes or []
        self.rd = {}
        self.headtags = headtags or []

    def __call__(self, path, meth='GET', cls=HTMLResponse):
        def _inner(f):
            @wraps(f)
            async def g(request):
                resp = await f(request)
                if not resp or isinstance(resp, str): resp = cls(resp)
                if isinstance(resp, Response): return resp
                if 'HX-Request' not in request.headers:
                    resp = wrap_root(resp, self.headtags)
                return cls(to_xml(resp))
            self.rd[(path,meth)] = Route(path, g, methods=[meth])
            return g
        return _inner

    @property
    def routes(self): return self.rt + list(self.rd.values())

class NotFoundException(HTTPException):
    def __init__(self): return super().__init__(404)

async def not_found(request: Request, exc: NotFoundException):
    return HTMLResponse(content='not found', status_code=exc.status_code)

exception_handlers = { NotFoundException: not_found }

htmxscr = Script(
    src="https://unpkg.com/htmx.org@1.9.12", crossorigin="anonymous",
    integrity="sha384-ujb1lZYygJmzgSwoxRggbCHcjc0rB2XoQrxeTUQyRjrOnlCoYta87iKBWq3EsdM2")
picocss = Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/@picocss/pico@latest/css/pico.min.css")

rt = Router(headtags=[htmxscr, picocss])

@rt("/", 'POST')
async def add_item(request):
    data = await request.form()
    new_id = str(len(TODO_LIST) + 1)
    new_item = TodoItem(id=new_id, title=data['title'], done=False)
    TODO_LIST.append(new_item)
    return (Li(A(new_item.title, href='#',
                hx_get=f'/todos/{new_item.id}', hx_target="#current-todo",
                hx_on__after_request="console.log('Done making a request!')", 
                hx_on__before_request="console.log('Making a request!')"),
             id=f'todo-{new_item.id}'), # << This gets added to the list
             Div(new_todo_form(), hx_swap_oob='true', id='new-todo-form')) # << Reset the form

@rt("/{item_id}", 'PUT')
async def update_item(request):
    data = await request.json()
    item_id = request.path_params['item_id']
    todo_item = find_todo(item_id)
    todo_item.title = data['title']
    todo_item.done = data['done']
    return RedirectResponse("/", status_code=303)

@rt("/favicon.ico")
async def favicon(request): return FileResponse('favicon.ico', media_type='image/x-icon')

def find_todo(tid):
    try: return next(o for o in TODO_LIST if o.id==tid)
    except: raise NotFoundException() from None

@rt("/todos/{tid}", 'DELETE')
async def del_todo(request):
    todo = find_todo(request.path_params['tid'])
    TODO_LIST.remove(todo)
    return Div(hx_swap_oob='true', id='todo-details')

@rt("/todos/{tid}")
async def get_todo_by_id(request):
    todo = find_todo(request.path_params['tid'])
    btn = Button('delete', hx_delete=f'/todos/{todo.id}',
                 hx_target=f"#todo-{todo.id}", hx_swap="outerHTML")
    return Div(Div(todo.title), btn, id='todo-details')

def new_todo_form():
    return Form(
        Input(type="text", name="title", placeholder="New Todo"),
        Button("Add Todo", type="submit"),
        method="post",
        hx_post="/",
        hx_target="#todo-list",
        hx_swap="beforeend",
        id="new-todo-form",
    )

@rt("/")
async def get_todos(request):
    form = new_todo_form()
    elems = H1('Todo list'), form, Ul(*TODO_LIST, id="todo-list"), Div(id='current-todo')
    return (Title('TODO list'), Body(Main(*elems, cls='container')))

app = Starlette(debug=True, routes=rt.routes, exception_handlers=exception_handlers)