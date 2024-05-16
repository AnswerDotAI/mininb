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

@rt("/favicon.ico")
async def favicon(request): return FileResponse('favicon.ico', media_type='image/x-icon')

@rt("/", 'POST')
async def add_item(data: TodoItem):
    TODO_LIST.append(data)

@rt("/{item_title:str}", 'PUT')
async def update_item(item_title: str, data: TodoItem):
    todo_item = get_todo_by_title(item_title)
    todo_item.title = data.title
    todo_item.done = data.done

@rt("/todos/{todoid}", 'DELETE')
async def del_todo(request):
    todoid = request.path_params['todoid']
    TODO_LIST.remove(next(o for o in TODO_LIST if o.id == todoid))
    return Div(hx_swap_oob='true', id='todo-details')

@rt("/todos/{todoid}")
async def get_todo_by_id(request):
    todoid = request.path_params['todoid']
    try: todo = next(o for o in TODO_LIST if o.id == todoid)
    except: raise NotFoundException() from None
    btn = Button('delete', hx_delete=f'/todos/{todo.id}',
                 hx_target=f"#todo-{todo.id}",
                 hx_swap="outerHTML")
    return Div(Div(todo.title), btn, id='todo-details')

@rt("/")
async def get_todos(request):
    main = Main(H1('Todo list'), Ul(*TODO_LIST), Div(id='current-todo'), cls='container')
    return (Title('TODO list'), Body(main))

app = Starlette(debug=True, routes=rt.routes, exception_handlers=exception_handlers)
