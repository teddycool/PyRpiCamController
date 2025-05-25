import logging
import json
import requests

class LoggingSecureHandler(logging.Handler):
    """
    A custom logging handler that sends log records to a remote server
    using HTTPS with an API key for authentication.
    """
    def __init__(self, host, url, api_key, secure=True):
        """
        Initialize the handler.

        :param host: The host of the logging server (e.g., "your-log-server.com").
        :param url: The endpoint URL on the server (e.g., "/api/logs").
        :param api_key: The API key for authentication.
        :param secure: Whether to use HTTPS (default: True).
        """
        super().__init__()
        self.host = host
        self.url = url
        self.api_key = api_key
        self.secure = secure
        self.protocol = "https" if secure else "http"

    def emit(self, record):
        """
        Send the log record to the remote server.

        :param record: The log record to send.
        """
        try:
            # Format the log record as JSON
            log_entry = self.format(record)
            log_data = json.loads(log_entry)

            # Construct the full URL
            full_url = f"{self.protocol}://{self.host}{self.url}"

            # Send the log data as a POST request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            response = requests.post(full_url, headers=headers, json=log_data)

            # Check for errors in the response
            if response.status_code != 200:
                self.handleError(record)
        except Exception:
            self.handleError(record)

# Example usage:
if __name__ == "__main__":
    import logging

    # Example configuration
    host = "your-log-server.com"
    url = "/api/logs"
    api_key = "your_api_key_here"

    # Create a logger
    logger = logging.getLogger("secure_logger")
    logger.setLevel(logging.DEBUG)

    # Create the custom handler
    secure_handler = LoggingSecureHandler(host=host, url=url, api_key=api_key, secure=True)

    # Set a formatter for the handler
    formatter = logging.Formatter(json.dumps({
        'time': '%(asctime)s',
        'logname': '%(name)s',
        'logLevel': '%(levelname)s',
        'message': '%(message)s',
        'cpuid': '%(cpuid)s'
    }))
    secure_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(secure_handler)

    # Log a test message
    logger.info("This is a test log message.")