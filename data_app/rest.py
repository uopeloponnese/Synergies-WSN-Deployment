from flask_restful import Resource, request
from werkzeug.exceptions import NotFound, BadRequest
from flask import jsonify, send_from_directory


class Greet(Resource):
    @staticmethod
    def get(self):
        return {'message': 'Hello, welcome to the greet endpoint!'}

