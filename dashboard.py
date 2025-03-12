from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Global dictionary to store lap counts
lap_counts = {}

# HTML template for the dashboard
dashboard_html = """
<!doctype html>
<html>
    <head>
        <title>Race Lap Dashboard</title>
        <!-- Auto-refresh every 5 seconds -->
        <meta http-equiv="refresh" content="5">
    </head>
    <body>
        <h1>Race Lap Dashboard</h1>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr>
                <th>Race Number</th>
                <th>Lap Count</th>
            </tr>
            {% for num, count in lap_counts.items() %}
            <tr>
                <td>{{ num }}</td>
                <td>{{ count }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(dashboard_html, lap_counts=lap_counts)

@app.route('/update', methods=['POST'])
def update():
    global lap_counts
    data = request.get_json()
    if data is None:
        return jsonify({"status": "error", "message": "No JSON received"}), 400
    
    # Update the global lap_counts with the received data
    lap_counts = data
    print("Dashboard updated:", lap_counts)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # Run on all interfaces at port 5000
    app.run(host="0.0.0.0", port=5003)