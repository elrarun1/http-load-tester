from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
from http_load_tester import HTTPLoadTester
import asyncio
import yaml
import os
import shutil

# Get the absolute path of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Set the correct path for the templates folder (one level up from src)
template_dir = os.path.abspath(os.path.join(current_dir, '..', 'templates'))

print(f"Current directory: {current_dir}")
print(f"Template directory: {template_dir}")
print(f"Template directory exists: {os.path.exists(template_dir)}")
print(f"Files in template directory: {os.listdir(template_dir) if os.path.exists(template_dir) else 'N/A'}")

app = Flask(__name__, template_folder=template_dir)


# Swagger UI configuration
SWAGGER_URL = '/docs'
API_URL = '/openapi.yaml'


# Load and serve the OpenAPI spec
@app.route('/openapi.yaml')
def serve_openapi_spec():
    with open(os.path.join(current_dir, 'docs', 'openapi.yaml'), 'r') as f:
        spec = yaml.safe_load(f)
    return jsonify(spec)


swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "HTTP Load Tester API"
    }
)

app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering template: {str(e)}")
        return f"Error: {str(e)}", 500


@app.route('/run-test', methods=['GET', 'POST'])
def run_test():
    if request.method == 'GET':
        return jsonify({
            "error": "Method Not Allowed",
            "message": "This endpoint only accepts POST requests. Please use the web interface at the root URL or send a POST request with the appropriate JSON payload."
        }), 405

    try:
        config = request.json
        load_tester = HTTPLoadTester(
            url=config['url'],
            qps=config['qps'],
            duration=config['duration'],
            method=config['method'],
            headers=config.get('headers'),
            data=config.get('data'),
            concurrency=config.get('concurrency', 100)
        )

        asyncio.run(load_tester.run_test())
        results = load_tester.generate_report()

        if not results:
            return jsonify({'error': 'No results generated from the test'}), 500

        # Save plots
        output_dir = os.path.join(current_dir, 'output')
        os.makedirs(output_dir, exist_ok=True)
        latency_plot_path = os.path.join(output_dir, 'latency_distribution.png')
        status_plot_path = os.path.join(output_dir, 'status_code_distribution.png')
        load_tester.plot_latency_distribution(
            results['latencies'],
            results['p50_latency'],
            results['p90_latency'],
            results['p95_latency'],
            results['p99_latency'],
            latency_plot_path
        )
        load_tester.plot_status_code_distribution(
            results['status_codes'],
            status_plot_path
        )

        return jsonify({
            'results': results,
            'latency_plot': '/output/latency_distribution.png',
            'status_plot': '/output/status_code_distribution.png'
        })
    except Exception as e:
        app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/output/<path:filename>')
def serve_output(filename):
    return send_from_directory(os.path.join(current_dir, 'output'), filename)


@app.route('/clear', methods=['POST'])
def clear_data():
    try:
        # Clear output directory
        output_dir = os.path.join(current_dir, 'output')
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)

        return jsonify({'message': 'All data cleared successfully'}), 200
    except Exception as e:
        app.logger.error(f"An error occurred while clearing data: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)