import types, xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import partial
from litestar import MediaType, Litestar, get, post, put
from litestar.static_files import create_static_files_router
from litestar.exceptions import NotFoundException

def _attrmap(o):
    o = o.lstrip('_').replace('_','-')
    return dict(cls='class', klass='class', fr='for').get(o, o)

def xt(tag:str, *c, **kw):
    if len(c)==1 and isinstance(c[0], types.GeneratorType): c = tuple(c[0])
    elif len(c)==1 and isinstance(c[0],str): c = c[0]
    kw = {_attrmap(k):str(v) for k,v in kw.items()}
    return [tag.lower(),c,kw]

g = globals()
tags = '''html head title meta link style body div span p h1 h2 h3 h4 h5 h6 strong em b i u s
strike sub sup hr br img a link nav ul ol li dl dt dd table thead tbody tfoot tr th td caption
col colgroup form input textarea button select option label fieldset legend details summary main
header footer section article aside figure figcaption mark small iframe object embed param video
audio source canvas svg math script noscript template slot'''.split()
for o in tags: g[o.capitalize()] = partial(xt, o)

def to_xml(node:tuple):
    "Convert `node` to an XML string."
    def mk_el(tag, cs, attrs):
        el = ET.Element(tag, attrib=attrs)
        if isinstance(cs, tuple): el.extend([mk_el(*o) for o in cs])
        elif cs is not None: el.text = str(cs)
        return el

    root = mk_el(*node)
    ET.indent(root)
    return ET.tostring(root, encoding='unicode', short_empty_elements=False)

@dataclass
class TodoItem:
    id: int
    title: str
    done: bool
    def tag(self): return A(self.title, hx_get=f'/todos/{self.id}', hx_target="#current-todo", href='#')

TODO_LIST: list[TodoItem] = [
    TodoItem(0, title="Start writing TODO list", done=True),
    TodoItem(1, title="???", done=False),
    TodoItem(2, title="Profit", done=False),
]

def get_todo_by_title(todo_name) -> str:
    try: return next(o for o in TODO_LIST if o.title == todo_name).title
    except: raise NotFoundException(detail=f"TODO {todo_name!r} not found") from None

@get("/todos/{todoid:int}", media_type=MediaType.HTML)
async def get_todo_by_id(todoid:int) -> str:
    try: todo = next(o for o in TODO_LIST if o.id == todoid)
    except: raise NotFoundException(detail=f"TODO {todoid!r} not found") from None
    return to_xml(Div(Div(todo.title), A('delete', hx_delete=f'/todos/{todo.id}', href='#')))

@post("/")
async def add_item(data: TodoItem) -> list[TodoItem]:
    TODO_LIST.append(data)
    return TODO_LIST

@put("/{item_title:str}")
async def update_item(item_title: str, data: TodoItem) -> list[TodoItem]:
    todo_item = get_todo_by_title(item_title)
    todo_item.title = data.title
    todo_item.done = data.done
    return TODO_LIST

@get("/", media_type=MediaType.HTML)
async def get_list(done: bool|None = None) -> str:
    todos = TODO_LIST if done is None else [
        item for item in TODO_LIST if item.done == done]
    tlist = Ul(Li(item.tag()) for item in todos)
    elems = [H1('TODO list'), tlist, Div(id='current-todo')]
    htmxscr = Script(src="https://unpkg.com/htmx.org@1.9.12",
                     integrity="sha384-ujb1lZYygJmzgSwoxRggbCHcjc0rB2XoQrxeTUQyRjrOnlCoYta87iKBWq3EsdM2",
                     crossorigin="anonymous")
    head = [Title('TODO list'), htmxscr]
    res = Html(Head(*head), Body(*elems))
    return to_xml(res)

app = Litestar(
    route_handlers=[
        create_static_files_router(path="/static", directories=["static"]),
        get_list, add_item, update_item, get_todo_by_id
    ]
)
