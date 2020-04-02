mkdir -p ~/.streamlit/

echo "\
[general]\n\
email = \"dl.nguyen404@gmail.com\"\n\
" > ~/.streamlit/credentials.toml

echo "\
[server]\n\
headless = true\n\
enableCORS=false\n\
port = $PORT\n\
" > ~/.streamlit/config.toml

echo "pip install streamlit\n"
echo "pip install sqlalchemy\n"
echo "pip install plotly\n"