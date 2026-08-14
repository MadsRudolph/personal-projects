"""Quick test: enable listen mode, send a test NEC code, then wait for received signals."""
import asyncio
import aioesphomeapi

HOST = "192.168.50.148"
PORT = 6053
KEY = "AcucgZvupvHszlDRjRhOqVsBtBlrTeiPFtAZGu8c61c="


async def main():
    cli = aioesphomeapi.APIClient(HOST, PORT, "", noise_psk=KEY)
    print(f"Connecting to {HOST}:{PORT}...")
    await cli.connect(login=True)
    info = await cli.device_info()
    print(f"Connected: {info.name}")

    # Enable listen mode
    print("\n=== Enabling IR listen mode ===")
    await cli.execute_service(
        aioesphomeapi.UserService(
            name="set_ir_listen",
            key=0,
            args=[aioesphomeapi.UserServiceArg(name="enabled", type=aioesphomeapi.UserServiceArgType.BOOL)],
        ),
        data={"enabled": True},
    )
    print("Listen mode ON — point any remote at the receiver and press a button.")
    print("Check the serial log for 'Received ...' messages.\n")

    # Send a test NEC code (common TV power)
    print("=== Sending test NEC code (addr=0x04, cmd=0x08) ===")
    await cli.execute_service(
        aioesphomeapi.UserService(
            name="send_ir_nec",
            key=0,
            args=[
                aioesphomeapi.UserServiceArg(name="address", type=aioesphomeapi.UserServiceArgType.INT),
                aioesphomeapi.UserServiceArg(name="command", type=aioesphomeapi.UserServiceArgType.INT),
            ],
        ),
        data={"address": 0x04, "command": 0x08},
    )
    print("NEC signal sent! If wired correctly, the IR LED just flashed.")
    print("(Use a phone camera to see the IR LED — it glows purple/white on camera)\n")

    print("Waiting 15 seconds — press buttons on any remote aimed at the receiver...")
    await asyncio.sleep(15)

    await cli.disconnect()
    print("Done.")


asyncio.run(main())
