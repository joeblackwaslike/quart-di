# QuartDI

QuartDI is an extension for [Quart](https://quart.palletsprojects.com/en/latest/) that integrates a dependency injection framework called [DI](https://www.adriangb.com/di/) to provide [FastAPI-like dependency injection](https://fastapi.tiangolo.com/tutorial/dependencies/) capabilities to your views.

## Usage
To use Quart-DI with a Quart app, you have to create the extension and initialize it with the application object.  You can either pass the app object to the `QuartDI` constructor, or create the `di` object and defer initialization to later using `di.init_app(app)`.
```python
app = Quart(__name__)

# create and initialize in one
di = QuartDI(app)

# or create and initialize seperately
di = QuartDI()
di.init_app(app)

# or using the create_app factory pattern
di = QuartDI()

def create_app():
    app = Quart(__name__)
    di.init_app(app)
    return app

app = create_app()

### Injecting dependencies into views
You can either use the quart_di.inject decorator to decorate all the views you would like to inject into, or initialize `QuartDI` with `decorate_views=True` option.  The latter will automatically apply the inject decorator to all views in your application for you.

#### Using the decorator
```python
from quart import Quart
from quart_di import QuartDI, inject



app = Quart(__name__)
di = QuartDI(app)


class Item(BaseModel):
    name: str
    value: str


@inject
@app.route("/endpoint", methods="POST")
async def endpoint(item: Json[Item]):
    return item.dict()
```

#### Using decorate_views=True
```python
from quart import Quart
from quart_di import QuartDI



app = Quart(__name__)
di = QuartDI(app, decorate_views=True)


class Item(BaseModel):
    name: str
    value: str


@app.route("/endpoint", methods="POST")
async def endpoint(item: Json[Item]):
    return item.dict()
```


## Configuration
The `QuartDI` extension has the following signature:
```python
BindByTypeType = Tuple[Type, DependantBase[Any]]
BindCallableType = Callable[
    [Optional[inspect.Parameter], DependantBase[Any]], Optional[DependantBase[Any]]
]
DependencyType = Union[BindByTypeType, BindCallableType]


def __init__(
    self,
    app: Quart,
    container: Optional[Container] = None,
    container_state: Optional[ContainerState] = None,
    binds: Optional[Sequence[DependencyType]] = None,
    decorate_views: bool = False,
    encode_view_result: bool = True,
    view_result_encoder: Callable[[Any], Any] = jsonable_encoder,
    view_result_encoder_options: Optional[Dict[str, Any]] = None,
) -> None:
    ...
```
