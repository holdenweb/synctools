project := `uv version | awk '{print $1}'`
version := `uv version | awk '{print $2}'`


install:
    @echo {{version}} {{project}}
    if [ ! -f dist/{{project}}-{{version}}-py3-none-any.whl ]; then uv build ; fi
    uv tool install -U dist/{{project}}-{{version}}-py3-none-any.whl
