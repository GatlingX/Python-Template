from utils.llm.dspy_inference import DSPYInference
import dspy
import asyncio

class ExtractInfo(dspy.Signature):
    """Extract structured information from text."""
    text: str = dspy.InputField(desc="The text to extract information from")
    title: str = dspy.OutputField(desc="The title of the text")
    headings: list[str] = dspy.OutputField(desc="A list of headings in the text")
    entities: list[dict[str, str]] = dspy.OutputField(
        desc="a list of entities and their metadata"
    )

def web_search(query: str) -> str:
    """Search the web for information."""
    return "This is a test"

inf_module = DSPYInference(
    pred_signature=ExtractInfo,
    tools=[web_search]
)

result = asyncio.run(inf_module.run(
    text="Apple Inc. announced its latest iPhone 14 today."
    "The CEO, Tim Cook, highlighted its new features in a press release."
))

print(result.title)
print(result.headings)
print(result.entities)