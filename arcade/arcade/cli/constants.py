DEFAULT_CLOUD_HOST = "cloud.arcade-ai.com"
DEFAULT_ENGINE_HOST = "api.arcade-ai.com"

_style_block = b"""
<link rel="icon" href="https://cdn.arcade-ai.com/favicons/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="https://cdn.arcade-ai.com/favicons/apple-touch-icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="https://cdn.arcade-ai.com/favicons/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="https://cdn.arcade-ai.com/favicons/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="https://cdn.arcade-ai.com/favicons/apple-touch-icon.png">

<style>
    body {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        margin: 0;
        background: linear-gradient(135deg, #1a1a1a, #0f0f0f);
        font-family: Arial, sans-serif;
    }

    .container {
        background-color: #333;
        padding: 40px;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        width: 300px;
    }

    .container h2 {
        color: #fff;
        margin-bottom: 20px;
        text-align: center;
    }

    .container label {
        display: block;
        color: #bbb;
        margin-bottom: 5px;
        font-size: 14px;
    }

    .container input[type="text"],
    .container input[type="password"] {
        width: 100%;
        padding: 10px;
        margin-bottom: 15px;
        border: none;
        border-radius: 4px;
        background-color: #444;
        color: #ddd;
        font-size: 16px;
        box-sizing: border-box;
    }

    .container input[type="text"]::placeholder,
    .container input[type="password"]::placeholder {
        color: #aaa;
    }

    .container input[type="submit"] {
        width: 100%;
        padding: 10px;
        border: none;
        border-radius: 4px;
        background-color: #ED155D;
        color: #fff;
        font-size: 16px;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }

    .container input[type="submit"]:hover {
        background-color: #C0104A;
    }

    .message {
        background-color: #1e1e1e;
        padding: 10px;
        border-radius: 4px;
        margin-bottom: 15px;
        font-size: 14px;
        text-align: center;
    }
    .info {
        color: #fff;
    }

    .error {
        color: #ff4d4d;
    }

    .logo {
        display: block;
        max-width: 100%;
        max-height: 90px;
        margin: 0 auto 20px;
    }
</style>
"""

LOGIN_SUCCESS_HTML = (
    b"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Success!</title>
    """
    + _style_block
    + b"""
</head>
<body>
    <div class="container">
        <img src="https://cdn.arcade-ai.com/logos/a-icon.png" alt="Arcade logo" class="logo">
        <h2>Log in to Arcade CLI</h2>
        <p class="message info">Success! You can close this window.</p>
    </div>
</body>
</html>
"""
)

LOGIN_FAILED_HTML = (
    b"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login failed</title>
    """
    + _style_block
    + b"""
</head>
<body>
    <div class="container">
        <img src="https://cdn.arcade-ai.com/logos/a-icon.png" alt="Arcade logo" class="logo">
        <h2>Log in to Arcade CLI</h2>
        <p class="message error">Something went wrong. Please close this window and try again.</p>
    </div>
</body>
</html>
"""
)
