import asyncio
from prompt_toolkit.input import create_input

async def debug_keys():
    done = asyncio.Event()
    input_stream = create_input()

    def keys_ready():
        for key_press in input_stream.read_keys():
            # This prints the EXACT key string prompt_toolkit sees
            print(f"Detected Key -> key={repr(key_press.key)}")
            if key_press.key in ('escape', 'c-c'):
                done.set()

    print("Press Ctrl+Left / Ctrl+Right (Press Esc or Ctrl+C to exit):")
    with input_stream.raw_mode(), input_stream.attach(keys_ready):
        await done.wait()

asyncio.run(debug_keys())
