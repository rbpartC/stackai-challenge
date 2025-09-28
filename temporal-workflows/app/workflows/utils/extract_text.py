from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import requests
    from bs4 import BeautifulSoup


def extract_text_from_url(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text


if __name__ == "__main__":
    url = input("Enter the URL: ")
    text = extract_text_from_url(url)
    print(text)
