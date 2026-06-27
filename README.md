Start virtual environment with

````python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools
pip install -r requirements.txt```

if punkt has not been downloaded, in a python file run
```

    import nlkt
    nlkt.download('punkt')

```
````
