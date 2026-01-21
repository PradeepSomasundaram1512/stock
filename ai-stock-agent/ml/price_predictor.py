"""
ML Price Predictor - LSTM and XGBoost models for price prediction.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class MLPricePredictor:
    """
    Machine Learning Price Predictor using LSTM and XGBoost ensemble.
    """

    def __init__(self, model_dir: str = "models"):
        """Initialize the ML price predictor."""
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.lstm_model = None
        self.xgb_model = None
        self.scaler = None

        self.lookback_days = 60  # Use 60 days of history
        self.features_count = 50  # Number of technical features

    def prepare_features(
        self,
        df: pd.DataFrame,
        technical_indicators: Dict[str, Any]
    ) -> np.ndarray:
        """
        Prepare feature matrix from price data and indicators.

        Args:
            df: Price dataframe with OHLCV
            technical_indicators: Dict of calculated indicators

        Returns:
            Feature matrix
        """
        features = []

        # Price-based features
        df['returns'] = df['Close'].pct_change()
        df['log_returns'] = np.log(df['Close'] / df['Close'].shift(1))

        # Moving averages ratios
        for period in [5, 10, 20, 50, 100, 200]:
            col_name = f'ma{period}_ratio'
            df[col_name] = df['Close'] / df['Close'].rolling(period).mean()
            features.append(col_name)

        # Volatility features
        for period in [5, 10, 20]:
            col_name = f'volatility_{period}'
            df[col_name] = df['returns'].rolling(period).std()
            features.append(col_name)

        # Volume features
        df['volume_ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
        df['volume_std'] = df['Volume'].rolling(20).std()
        features.extend(['volume_ratio', 'volume_std'])

        # Price momentum
        for period in [5, 10, 20]:
            col_name = f'momentum_{period}'
            df[col_name] = df['Close'] - df['Close'].shift(period)
            features.append(col_name)

        # High-Low spread
        df['hl_spread'] = (df['High'] - df['Low']) / df['Close']
        features.append('hl_spread')

        # Add technical indicators
        if technical_indicators:
            # RSI
            if 'rsi' in technical_indicators:
                df['rsi'] = technical_indicators['rsi']
                features.append('rsi')

            # MACD
            if 'macd' in technical_indicators:
                df['macd'] = technical_indicators['macd']
                features.append('macd')

            if 'macd_signal' in technical_indicators:
                df['macd_signal_line'] = technical_indicators['macd_signal']
                features.append('macd_signal_line')

            # Bollinger Bands
            if 'bb_upper' in technical_indicators and 'bb_lower' in technical_indicators:
                df['bb_width'] = (
                    technical_indicators['bb_upper'] - technical_indicators['bb_lower']
                ) / df['Close']
                df['bb_position'] = (
                    df['Close'] - technical_indicators['bb_lower']
                ) / (technical_indicators['bb_upper'] - technical_indicators['bb_lower'])
                features.extend(['bb_width', 'bb_position'])

        # Fill NaN values
        df[features] = df[features].fillna(method='ffill').fillna(0)

        return df[features].values

    def create_sequences(
        self,
        features: np.ndarray,
        target: np.ndarray,
        lookback: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for LSTM training.

        Args:
            features: Feature matrix
            target: Target values (future prices)
            lookback: Number of days to look back

        Returns:
            X, y arrays for training
        """
        X, y = [], []

        for i in range(lookback, len(features)):
            X.append(features[i-lookback:i])
            y.append(target[i])

        return np.array(X), np.array(y)

    def train_lstm(
        self,
        df: pd.DataFrame,
        technical_indicators: Dict[str, Any],
        forecast_days: int = 5
    ):
        """
        Train LSTM model for price prediction.

        Args:
            df: Historical price data
            technical_indicators: Technical indicators
            forecast_days: Number of days to forecast
        """
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
            from tensorflow.keras.optimizers import Adam
            from sklearn.preprocessing import MinMaxScaler

            logger.info("Training LSTM model...")

            # Prepare features
            features = self.prepare_features(df, technical_indicators)

            # Target: future price (N days ahead)
            target = df['Close'].shift(-forecast_days).values

            # Remove NaN rows
            valid_idx = ~np.isnan(target)
            features = features[valid_idx]
            target = target[valid_idx]

            # Scale features
            self.scaler = MinMaxScaler()
            features_scaled = self.scaler.fit_transform(features)

            # Create sequences
            X, y = self.create_sequences(features_scaled, target, self.lookback_days)

            # Train/test split (80/20)
            split = int(0.8 * len(X))
            X_train, X_test = X[:split], X[split:]
            y_train, y_test = y[:split], y[split:]

            # Build LSTM model
            model = Sequential([
                LSTM(128, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])),
                Dropout(0.2),
                LSTM(64, return_sequences=True),
                Dropout(0.2),
                LSTM(32),
                Dropout(0.2),
                Dense(16, activation='relu'),
                Dense(1)
            ])

            model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])

            # Train model
            history = model.fit(
                X_train, y_train,
                epochs=50,
                batch_size=32,
                validation_data=(X_test, y_test),
                verbose=0
            )

            self.lstm_model = model

            # Evaluate
            test_loss, test_mae = model.evaluate(X_test, y_test, verbose=0)
            logger.info(f"LSTM trained - Test MAE: ${test_mae:.2f}")

            return history

        except ImportError:
            logger.warning("TensorFlow not installed. LSTM model unavailable.")
            return None

    def train_xgboost(
        self,
        df: pd.DataFrame,
        technical_indicators: Dict[str, Any],
        forecast_days: int = 5
    ):
        """
        Train XGBoost model for price prediction.

        Args:
            df: Historical price data
            technical_indicators: Technical indicators
            forecast_days: Number of days to forecast
        """
        try:
            import xgboost as xgb

            logger.info("Training XGBoost model...")

            # Prepare features
            features = self.prepare_features(df, technical_indicators)

            # Target: future price change percentage
            target = ((df['Close'].shift(-forecast_days) - df['Close']) / df['Close'] * 100).values

            # Remove NaN rows
            valid_idx = ~np.isnan(target)
            features = features[valid_idx]
            target = target[valid_idx]

            # Train/test split
            split = int(0.8 * len(features))
            X_train, X_test = features[:split], features[split:]
            y_train, y_test = target[:split], target[split:]

            # Train XGBoost
            model = xgb.XGBRegressor(
                objective='reg:squarederror',
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42
            )

            model.fit(X_train, y_train)

            self.xgb_model = model

            # Evaluate
            from sklearn.metrics import mean_absolute_error
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)

            logger.info(f"XGBoost trained - Test MAE: {mae:.2f}%")

            return model

        except ImportError:
            logger.warning("XGBoost not installed. XGBoost model unavailable.")
            return None

    def predict(
        self,
        df: pd.DataFrame,
        technical_indicators: Dict[str, Any],
        forecast_days: int = 5
    ) -> Dict[str, Any]:
        """
        Make price prediction using ensemble of models.

        Args:
            df: Recent price data
            technical_indicators: Technical indicators
            forecast_days: Number of days to forecast

        Returns:
            Prediction results
        """
        current_price = df['Close'].iloc[-1]

        predictions = []
        weights = []

        # LSTM prediction
        if self.lstm_model and self.scaler:
            try:
                from sklearn.preprocessing import MinMaxScaler

                features = self.prepare_features(df, technical_indicators)
                features_scaled = self.scaler.transform(features[-self.lookback_days:])
                features_reshaped = features_scaled.reshape(1, self.lookback_days, -1)

                lstm_pred = self.lstm_model.predict(features_reshaped, verbose=0)[0][0]
                predictions.append(lstm_pred)
                weights.append(0.6)  # 60% weight to LSTM

                logger.info(f"LSTM prediction: ${lstm_pred:.2f}")

            except Exception as e:
                logger.error(f"LSTM prediction error: {e}")

        # XGBoost prediction
        if self.xgb_model:
            try:
                features = self.prepare_features(df, technical_indicators)
                xgb_pred_pct = self.xgb_model.predict(features[-1:].reshape(1, -1))[0]
                xgb_pred = current_price * (1 + xgb_pred_pct / 100)

                predictions.append(xgb_pred)
                weights.append(0.4)  # 40% weight to XGBoost

                logger.info(f"XGBoost prediction: ${xgb_pred:.2f} ({xgb_pred_pct:+.2f}%)")

            except Exception as e:
                logger.error(f"XGBoost prediction error: {e}")

        if not predictions:
            return {
                'predicted_price': current_price,
                'predicted_change_pct': 0,
                'confidence': 0,
                'models_used': []
            }

        # Ensemble prediction (weighted average)
        ensemble_pred = np.average(predictions, weights=weights)
        pred_change_pct = ((ensemble_pred - current_price) / current_price) * 100

        # Calculate confidence based on model agreement
        if len(predictions) > 1:
            std = np.std(predictions)
            confidence = max(0, min(1, 1 - (std / current_price)))
        else:
            confidence = 0.7  # Default confidence for single model

        return {
            'current_price': round(current_price, 2),
            'predicted_price': round(ensemble_pred, 2),
            'predicted_change_pct': round(pred_change_pct, 2),
            'forecast_days': forecast_days,
            'confidence': round(confidence, 2),
            'models_used': [
                'LSTM' if self.lstm_model else None,
                'XGBoost' if self.xgb_model else None
            ],
            'lstm_prediction': round(predictions[0], 2) if self.lstm_model and predictions else None,
            'xgb_prediction': round(predictions[-1], 2) if self.xgb_model and predictions else None
        }

    def save_models(self, ticker: str):
        """Save trained models to disk."""
        try:
            if self.lstm_model:
                self.lstm_model.save(self.model_dir / f"{ticker}_lstm.h5")

            if self.xgb_model:
                with open(self.model_dir / f"{ticker}_xgb.pkl", 'wb') as f:
                    pickle.dump(self.xgb_model, f)

            if self.scaler:
                with open(self.model_dir / f"{ticker}_scaler.pkl", 'wb') as f:
                    pickle.dump(self.scaler, f)

            logger.info(f"Models saved for {ticker}")

        except Exception as e:
            logger.error(f"Error saving models: {e}")

    def load_models(self, ticker: str):
        """Load trained models from disk."""
        try:
            from tensorflow.keras.models import load_model

            lstm_path = self.model_dir / f"{ticker}_lstm.h5"
            if lstm_path.exists():
                self.lstm_model = load_model(lstm_path)
                logger.info(f"Loaded LSTM model for {ticker}")

        except Exception as e:
            logger.warning(f"Could not load LSTM model: {e}")

        try:
            xgb_path = self.model_dir / f"{ticker}_xgb.pkl"
            if xgb_path.exists():
                with open(xgb_path, 'rb') as f:
                    self.xgb_model = pickle.load(f)
                logger.info(f"Loaded XGBoost model for {ticker}")

        except Exception as e:
            logger.warning(f"Could not load XGBoost model: {e}")

        try:
            scaler_path = self.model_dir / f"{ticker}_scaler.pkl"
            if scaler_path.exists():
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info(f"Loaded scaler for {ticker}")

        except Exception as e:
            logger.warning(f"Could not load scaler: {e}")


# Singleton instance cache
_ml_predictor_instances = {}


def get_ml_predictor(ticker: str = None) -> MLPricePredictor:
    """Get or create ML predictor instance."""
    global _ml_predictor_instances

    if ticker and ticker in _ml_predictor_instances:
        return _ml_predictor_instances[ticker]

    predictor = MLPricePredictor()

    if ticker:
        predictor.load_models(ticker)
        _ml_predictor_instances[ticker] = predictor

    return predictor
