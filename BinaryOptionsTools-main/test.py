import pandas as pd
from BinaryOptionsTools import pocketoption
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import torch.optim as optim
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator
import time
# Define a basic neural network
class BinaryOptionsModel(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(BinaryOptionsModel, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.relu2 = nn.ReLU()
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.relu2(x)
        x = self.fc3(x)
        x = self.sigmoid(x)
        return x
# Load the session and connect to the PocketOption API
ssid = (r'42["auth",{"session":"n6ghkt8nk931jj6ffljoj8knj3","isDemo":1,"uid":85249466,"platform":2}]')

api = pocketoption(ssid, True)

# Get current balance
print(f"GET BALANCE: {api.GetBalance()}")

# Fetch candle data
df = api.GetCandles("EURUSD_otc", 1, count=420)
print(df)

# Preprocess the data (example assumes df has the right structure)
def preprocess_data(df):
    data = df
    # Calculate RSI
    rsi_period = 14
    data['rsi'] = RSIIndicator(close=data['close'], window=rsi_period).rsi()

    # Calculate MACD
    macd = MACD(close=data['close'])
    data['macd'] = macd.macd()
    data['macd_signal'] = macd.macd_signal()

    # Calculate Moving Averages
    sma_period = 50
    ema_period = 20
    data['sma'] = SMAIndicator(close=data['close'], window=sma_period).sma_indicator()
    data['ema'] = EMAIndicator(close=data['close'], window=ema_period).ema_indicator()

    # Drop any NaN values generated by the indicators
    data.dropna(inplace=True)

    # Define the feature columns, including the new signals
    features = ['open', 'high', 'low', 'close', 'rsi', 'macd', 'macd_signal', 'sma', 'ema']

    # Define a future prediction window (e.g., 5 periods ahead)
    prediction_window = 5

    # Create the target column: 1 if future close price is higher, else 0
    data['target'] = (data['close'].shift(-prediction_window) > data['close']).astype(int)


    # Extract features and target
    X = data[features].values
    y = data['target'].values

    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(X)

    # Convert to torch tensor
    features_tensor = torch.tensor(features_scaled, dtype=torch.float32)
    
    return features_tensor

while True:
    try:
        # Preprocess the fetched data
        X = preprocess_data(df)

        # Initialize the model (ensure that the architecture matches the trained model)
        input_size = 9  # Number of features
        hidden_size = 640         # Same hidden size as during training
        output_size = 1          # Single output (binary classification: "put" or "call")

        model = BinaryOptionsModel(input_size, hidden_size, output_size)

        # Load the saved model
        model.load_state_dict(torch.load(r"C:\Users\vigop\BinaryOptionsTools\binary_options_model2.pth"))

        # Set the model to evaluation mode (since we're making predictions)
        model.eval()

        # Make predictions
        with torch.no_grad():
            outputs = model(X)
            predictions = (outputs > 0.5).float()  # Binary prediction: 1 for call, 0 for put

        # Example of taking action based on predictions
        last_prediction = predictions[-1].item()

        if last_prediction == 1:
            print("Placing a 'call' trade.")
            # api.Trade('EURUSD_otc', direction='call', amount=1)  # Uncomment to place a call trade
            api.Call(10, "EURUSD_otc", 5)
            time.sleep(1)
        else:
            print("Placing a 'put' trade.")
            # api.Trade('EURUSD_otc', direction='put', amount=1)  # Uncomment to place a put trade
            api.Put(10, "EURUSD_otc", 5)
            time.sleep(1)
        time.sleep(1)
    except KeyboardInterrupt:
        break