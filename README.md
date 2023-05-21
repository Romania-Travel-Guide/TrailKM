# trailKM.py

`trailKM.py` is a Python script that utilizes the Outdooractive APIs to retrieve information about trails in a specified region. It calculates the total length and duration required to cover all the trails within that region.

## Prerequisites

Before running the script, ensure that you have the following:

- Python 3.x installed on your machine
- An API key from Outdooractive (available at [Outdooractive Developer Portal](https://developers.outdooractive.com))

## Installation

1. Clone the repository to your local machine using the following command:
   ```shell
   git clone https://github.com/Clustmart/trailKM.py.git
   ```

2. Navigate to the project directory:
   ```shell
   cd trailKM.py
   ```

3. Install the required dependencies by executing the following command:
   ```shell
   pip install -r requirements.txt
   ```

## Usage

To use the `trailKM.py` script, follow these steps:

1. Rename the file (`config.example`) to (`config.ini`) and open it in a text editor.

2. Replace `<YOUR_API_KEY>` with your Outdooractive API key and `<YOUR-PROJECT>` with your Outdooractive project name. 
  
3. Save the changes.

4. Run the script using the following command:
   ```shell
   python trailKM.py
   ```

5. The script will retrieve the trail data from Outdooractive APIs and calculate the total length and duration to cover all the trails in the specified region. The results will be displayed in the console.

## Contributing

Contributions to `trailKM.py` are welcome! If you find any issues or have ideas for improvements, please submit them via GitHub issues. Feel free to fork the repository and submit pull requests for any enhancements.

## License

This project is licensed under the [MIT License](LICENSE).

## Disclaimer

Please note that the `trailKM.py` script is provided as-is without any warranty. It is the user's responsibility to ensure compliance with the terms and conditions of the Outdooractive APIs and any other relevant services or APIs used within the script.

---
