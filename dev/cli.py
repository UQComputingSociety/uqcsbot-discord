import runpy
from dotenv import load_dotenv


def main():
    print("Starting UQCSbot Dev")
    load_dotenv()
    runpy.run_module("uqcsbot")


if __name__ == "__main__":
    main()
