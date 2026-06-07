import json
import os

log_path = r"C:\Users\joako\.gemini\antigravity-ide\brain\67805830-931c-45df-8bf5-bfa9a9f5dc35\.system_generated\logs\transcript.jsonl"
output_path = r"C:\Users\joako\.gemini\antigravity-ide\brain\2f13c44b-d7af-416d-94c6-e44fab9e530d\scratch\extracted_conv_details.txt"

if not os.path.exists(log_path):
    print("Error: path does not exist")
    exit(1)

with open(log_path, "r", encoding="utf-8") as f:
    steps = [json.loads(line) for line in f if line.strip()]

with open(output_path, "w", encoding="utf-8") as out:
    out.write("=== CONVERSATION 67805830-931c-45df-8bf5-bfa9a9f5dc35 DETAILS ===\n\n")
    for idx, step in enumerate(steps):
        step_type = step.get("type", "")
        source = step.get("source", "")
        content = step.get("content", "")
        tool_calls = step.get("tool_calls", [])
        
        out.write(f"--- STEP {idx+1} (Type: {step_type}, Source: {source}) ---\n")
        if content:
            out.write(f"Content:\n{content}\n")
        if tool_calls:
            out.write("Tool Calls:\n")
            for tc in tool_calls:
                out.write(f"  Tool: {tc.get('name')}\n")
                out.write(f"  Arguments: {json.dumps(tc.get('args'))}\n")
        out.write("\n" + "="*50 + "\n\n")

print(f"Details extracted to: {output_path}")
