from openai import OpenAI
client = OpenAI(api_key="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")

response = client.images.generate(
  model="dall-e-2",
  prompt="aesthetic purple background wallpaper image",
  size="1024x1024",
  quality="standard",
  n=1,
)

image_url = response.data[0].url

print(image_url)