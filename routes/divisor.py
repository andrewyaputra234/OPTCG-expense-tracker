from flask import Blueprint, request, jsonify

divisor_bp = Blueprint('divisor', __name__)

@divisor_bp.route('/', methods=['POST'])
def calculate_division():
    data = request.get_json()
    number = data.get('number')
    divisor = data.get('divisor')

    if number is None or divisor is None:
        return jsonify({"error": "Please provide 'number' and 'divisor' fields"}), 400

    try:
        number = float(number)
        divisor = float(divisor)
        if divisor == 0:
            raise ZeroDivisionError
        result = number / divisor
    except ValueError:
        return jsonify({"error": "Invalid number or divisor format"}), 400
    except ZeroDivisionError:
        return jsonify({"error": "Division by zero is not allowed"}), 400

    return jsonify({
        "number": number,
        "divisor": divisor,
        "result": result
    })
