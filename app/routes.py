from flask import Blueprint, jsonify, request
from app.models import Product
from app.services import ai_model

main = Blueprint('main', __name__)

@main.route('/items', methods=['GET'])
def get_items():
    return jsonify([])

@main.route('/items/<int:id>', methods=['GET'])
def get_item(id):
    return jsonify([])

@main.route('/recommend', methods=['GET'])
def call_model():
    return jsonify(ai_model.get_data())