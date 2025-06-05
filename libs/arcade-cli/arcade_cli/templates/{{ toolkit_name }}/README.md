<div style="display: flex; justify-content: center; align-items: center;">
  <img
    src="https://docs.arcade.dev/images/logo/arcade-logo.png"
    style="width: 250px;"
  >
</div>

<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 8px;">
  {% if toolkit_author_name -%}
  <img src="https://img.shields.io/github/v/release/{{ toolkit_author_name }}/{{ toolkit_name }}" alt="GitHub release" style="margin: 0 2px;">
  {% endif -%}
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python version" style="margin: 0 2px;">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License" style="margin: 0 2px;">
  <img src="https://img.shields.io/pypi/v/{{ package_name }}" alt="PyPI version" style="margin: 0 2px;">
</div>
{% if toolkit_author_name -%}
<div style="display: flex; justify-content: center; align-items: center;">
  <a href="https://github.com/{{ toolkit_author_name }}/{{ toolkit_name }}" target="_blank">
    <img src="https://img.shields.io/github/stars/{{ toolkit_author_name }}/{{ toolkit_name }}" alt="GitHub stars" style="margin: 0 2px;">
  </a>
  <a href="https://github.com/{{ toolkit_author_name }}/{{ toolkit_name }}/fork" target="_blank">
    <img src="https://img.shields.io/github/forks/{{ toolkit_author_name }}/{{ toolkit_name }}" alt="GitHub forks" style="margin: 0 2px;">
  </a>
</div>
{% endif %}

<br>
<br>

# Arcade {{ toolkit_name }} Toolkit
{% if toolkit_description -%}
{{ toolkit_description }}
{% endif -%}
## Features

- The {{ toolkit_name }} toolkit does not have any features yet.

## Development

Read the docs on how to create a toolkit [here](https://docs.arcade.dev/home/build-tools/create-a-toolkit)