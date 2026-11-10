import httpx

URL = "http://localhost:8000/graphql"

operations = " ".join(
    f'f{i}: likeCourse(id: "api-design") {{ course {{ likes }} }}'
    for i in range(1, 13)
)

response = httpx.post(URL, json={"query": f"mutation {{ {operations} }}"})
body = response.json()

print("HTTP status:", response.status_code)
if body.get("errors"):
    print("error:", body["errors"][0]["message"])
else:
    print("likes:", [body["data"][f"f{i}"]["course"]["likes"] for i in range(1, 13)])
print("SQL queries:", response.headers.get("x-sql-queries"))