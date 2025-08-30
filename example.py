from ollama import Client

from rich import print

client = Client()

#print(client.list().models)

for model_data in client.list().models:
    model_name = model_data.get('model')
    #print(model_data)
    model = client.show(model_name).details
    #print(model)
    if model:
        family = model.get('family')
        print(family)
        if family:
            model_info = client.show(model_name).modelinfo
            if model_info:
                context_length = model_info[f'{family}.context_length']
                print(context_length)
