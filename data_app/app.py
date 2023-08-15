import rest
import json
from flask import Flask, make_response, Response
from flask_restful import Api

app = Flask(__name__)
api = Api(app)


@api.representation('application/json')
def output_json(data, code=None, headers=None):
    json_response = json.dumps(data, indent=4)
    return Response(json_response, status=200, mimetype='application/json')


# endpoints
# api.add_resource(rest.Greet, '/greet', resource_class_kwargs={'representations': {'application/json': output_json}})
api.add_resource(rest.Greet)

if __name__ == "__main__":
    # ekkinisi tou server se ola ta interfaces tou, me default port tin 5000
    app.run(host="0.0.0.0")  # default port 5000
    # app.run(host="0.0.0.0", ssl_context=('ssl/certificate.crt', 'ssl/private.key'))  # default port 5000
