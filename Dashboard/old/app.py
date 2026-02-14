
import streamlit as st
import os
import subprocess

# python -m streamlit run Dashboard/ifc-viewer/app.py

st.set_page_config(layout="wide")
st.title("IFC Lite Viewer Integration")
st.markdown(
	'''<style>
	.viewer-iframe {
		width: 80%;
		height: 800px;
		border: none;
		margin: 0 auto;
		display: block;
	}
	</style>''', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload IFC file", type="ifc")
if uploaded_file:
	static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
	os.makedirs(static_dir, exist_ok=True)
	save_path = os.path.join(static_dir, uploaded_file.name)
	with open(save_path, "wb") as f:
		f.write(uploaded_file.getbuffer())
	# ...existing code...

	# Start HTTP server for static directory if not already running
	import socket
	def is_port_in_use(port):
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			return s.connect_ex(("localhost", port)) == 0

	if not is_port_in_use(8080):
		cors_script = os.path.join(os.path.dirname(__file__), '..', 'serve_static_with_cors.py')
		subprocess.Popen([
			"python", cors_script, static_dir
		], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		st.info("Started static file server with CORS on port 8080.")

	# Generate the file URL for the new server (use 127.0.0.1:8090)
	file_url = f"http://127.0.0.1:8090/{uploaded_file.name}"

	# Embed the viewer with the file URL as a query parameter
	viewer_url = f"http://localhost:3000/?file_url={file_url}"
	st.markdown(
		f'<iframe class="viewer-iframe" src="{viewer_url}"></iframe>',
		unsafe_allow_html=True
	)

