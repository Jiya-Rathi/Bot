import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re


class ColumnMapper:
    """Automatically detects and maps CSV columns to standardized format for financial analysis."""
    
    def __init__(self):
        # Standard column mappings for different bank formats
        self.column_patterns = {
            'date': [
                'date', 'post date', 'posting date', 'transaction date', 'effective date',
                'trans date', 'process date', 'posted', 'timestamp', 'time', 'fecha'
            ],
            'description': [
                'description', 'memo', 'reference', 'details', 'payee', 'merchant',
                'transaction details', 'trans desc', 'bank ref', 'client ref',
                'note', 'comments', 'narrative', 'concepto'
            ],
            'amount': [
                'amount', 'transaction amount', 'trans amount', 'value', 'sum',
                'net amount', 'total', 'monto', 'importe'
            ],
            'credit': [
                'credit', 'credit amount', 'deposits', 'income', 'inflow',
                'credit amt', 'cr', 'deposit amount', 'ingreso'
            ],
            'debit': [
                'debit', 'debit amount', 'withdrawals', 'expense', 'outflow',
                'debit amt', 'dr', 'withdrawal amount', 'gasto'
            ],
            'balance': [
                'balance', 'running balance', 'account balance', 'current balance',
                'ending balance', 'bal', 'saldo'
            ]
        }
        
        # Date formats to try when parsing dates
        self.date_formats = [
            '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y',
            '%Y/%m/%d', '%d-%b-%y', '%d-%b-%Y', '%b-%d-%Y', '%Y-%m-%d %H:%M:%S',
            '%m/%d/%y', '%d/%m/%y', '%y-%m-%d'
        ]
    
    def auto_map_columns(self, df: pd.DataFrame) -> Dict:
        """
        Automatically detect and map CSV columns to standard format.
        
        Returns:
            dict: Mapping results with detected columns and confidence scores
        """
        result = {
            'success': False,
            'mappings': {},
            'confidence_scores': {},
            'standardized_df': None,
            'suggestions': [],
            'warnings': []
        }
        
        try:
            # Step 1: Detect column types
            detected_columns = self._detect_column_types(df)
            
            # Step 2: Create mappings with confidence scores
            mappings = self._create_column_mappings(df, detected_columns)
            result['mappings'] = mappings
            result['confidence_scores'] = self._calculate_confidence_scores(df, mappings)
            
            # Step 3: Create standardized DataFrame
            standardized_df = self._create_standardized_dataframe(df, mappings)
            if standardized_df is not None:
                result['standardized_df'] = standardized_df
                result['success'] = True
            
            # Step 4: Generate suggestions and warnings
            result['suggestions'] = self._generate_mapping_suggestions(mappings, result['confidence_scores'])
            result['warnings'] = self._generate_mapping_warnings(df, mappings)
            
            return result
            
        except Exception as e:
            result['error'] = f"Error during column mapping: {str(e)}"
            return result
    
    def _detect_column_types(self, df: pd.DataFrame) -> Dict:
        """Detect the likely type of each column."""
        detected = {}
        
        for col in df.columns:
            col_type = self._classify_column(df[col], col)
            detected[col] = col_type
        
        return detected
    
    def _classify_column(self, series: pd.Series, col_name: str) -> str:
        """Classify a single column based on name and content."""
        col_name_lower = str(col_name).lower().strip()
        
        # Check name patterns first
        for col_type, patterns in self.column_patterns.items():
            if any(pattern in col_name_lower for pattern in patterns):
                # Verify with content analysis
                if self._verify_column_type(series, col_type):
                    return col_type
        
        # If name doesn't match, analyze content
        return self._analyze_column_content(series)
    
    def _verify_column_type(self, series: pd.Series, expected_type: str) -> bool:
        """Verify that column content matches expected type."""
        sample_size = min(20, len(series.dropna()))
        if sample_size == 0:
            return False
        
        sample = series.dropna().head(sample_size)
        
        if expected_type == 'date':
            return self._is_date_column(sample)
        elif expected_type in ['amount', 'credit', 'debit', 'balance']:
            return self._is_numeric_column(sample)
        elif expected_type == 'description':
            return self._is_text_column(sample)
        
        return False
    
    def _analyze_column_content(self, series: pd.Series) -> str:
        """Analyze column content to determine type."""
        sample_size = min(20, len(series.dropna()))
        if sample_size == 0:
            return 'unknown'
        
        sample = series.dropna().head(sample_size)
        
        # Check if it's a date column
        if self._is_date_column(sample):
            return 'date'
        
        # Check if it's numeric (could be amount, balance, etc.)
        if self._is_numeric_column(sample):
            # Try to determine if it's amount vs balance
            numeric_values = pd.to_numeric(sample, errors='coerce')
            if numeric_values.min() < 0:  # Has negative values, likely amounts
                return 'amount'
            else:
                return 'balance'  # Positive only, might be balance
        
        # Default to description for text columns
        if self._is_text_column(sample):
            return 'description'
        
        return 'unknown'
    
    def _is_date_column(self, sample: pd.Series) -> bool:
        """Check if sample values look like dates."""
        date_count = 0
        total_count = len(sample)
        
        for value in sample:
            if self._looks_like_date(str(value)):
                date_count += 1
        
        return (date_count / total_count) > 0.7
    
    def _is_numeric_column(self, sample: pd.Series) -> bool:
        """Check if sample values are numeric."""
        numeric_series = pd.to_numeric(sample, errors='coerce')
        numeric_count = numeric_series.notna().sum()
        return (numeric_count / len(sample)) > 0.7
    
    def _is_text_column(self, sample: pd.Series) -> bool:
        """Check if sample contains meaningful text."""
        if sample.dtype != 'object':
            return False
        
        # Check average text length
        avg_length = sample.astype(str).str.len().mean()
        return avg_length > 5  # Meaningful text usually longer than 5 characters
    
    def _looks_like_date(self, value: str) -> bool:
        """Check if a string value looks like a date."""
        # Try parsing with known formats
        for fmt in self.date_formats:
            try:
                datetime.strptime(str(value)[:19], fmt)
                return True
            except ValueError:
                continue
        
        # Check with regex patterns
        date_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\d{1,2}-\w{3}-\d{2,4}',
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, str(value)):
                return True
        
        return False
    
    def _create_column_mappings(self, df: pd.DataFrame, detected_columns: Dict) -> Dict:
        """Create the best possible column mappings."""
        mappings = {
            'date': None,
            'description': None,
            'amount': None,
            'credit': None,
            'debit': None,
            'balance': None
        }
        
        # Create reverse mapping for priority selection
        type_columns = {}
        for col, col_type in detected_columns.items():
            if col_type not in type_columns:
                type_columns[col_type] = []
            type_columns[col_type].append(col)
        
        # Map essential columns first
        for required_type in ['date', 'description']:
            if required_type in type_columns:
                # If multiple columns of same type, choose the best one
                best_col = self._select_best_column(df, type_columns[required_type], required_type)
                mappings[required_type] = best_col
        
        # Handle amount columns (can be single amount or separate credit/debit)
        if 'amount' in type_columns:
            mappings['amount'] = self._select_best_column(df, type_columns['amount'], 'amount')
        else:
            # Look for separate credit/debit columns
            if 'credit' in type_columns:
                mappings['credit'] = self._select_best_column(df, type_columns['credit'], 'credit')
            if 'debit' in type_columns:
                mappings['debit'] = self._select_best_column(df, type_columns['debit'], 'debit')
        
        # Map balance if available
        if 'balance' in type_columns:
            mappings['balance'] = self._select_best_column(df, type_columns['balance'], 'balance')
        
        return {k: v for k, v in mappings.items() if v is not None}
    
    def _select_best_column(self, df: pd.DataFrame, candidates: List[str], col_type: str) -> Optional[str]:
        """Select the best column from candidates for a given type."""
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Score each candidate
        scores = {}
        for col in candidates:
            score = 0
            col_name_lower = col.lower()
            
            # Name-based scoring
            if col_type in self.column_patterns:
                for pattern in self.column_patterns[col_type]:
                    if pattern in col_name_lower:
                        # Exact match gets higher score
                        if pattern == col_name_lower:
                            score += 10
                        else:
                            score += 5
                        break
            
            # Content-based scoring
            non_null_count = df[col].notna().sum()
            score += (non_null_count / len(df)) * 3  # Completeness score
            
            # Type-specific scoring
            if col_type == 'date':
                score += self._score_date_column(df[col])
            elif col_type in ['amount', 'credit', 'debit', 'balance']:
                score += self._score_numeric_column(df[col])
            elif col_type == 'description':
                score += self._score_text_column(df[col])
            
            scores[col] = score
        
        # Return column with highest score
        return max(scores, key=scores.get)
    
    def _score_date_column(self, series: pd.Series) -> float:
        """Score a date column based on parseability."""
        sample = series.dropna().head(10)
        parseable_count = 0
        
        for value in sample:
            if self._looks_like_date(str(value)):
                parseable_count += 1
        
        return (parseable_count / len(sample)) * 5 if len(sample) > 0 else 0
    
    def _score_numeric_column(self, series: pd.Series) -> float:
        """Score a numeric column based on validity."""
        numeric_series = pd.to_numeric(series, errors='coerce')
        valid_count = numeric_series.notna().sum()
        total_count = len(series.dropna())
        
        return (valid_count / total_count) * 5 if total_count > 0 else 0
    
    def _score_text_column(self, series: pd.Series) -> float:
        """Score a text column based on content quality."""
        if series.dtype != 'object':
            return 0
        
        sample = series.dropna().head(10)
        if len(sample) == 0:
            return 0
        
        avg_length = sample.astype(str).str.len().mean()
        # Prefer columns with meaningful text length
        if avg_length > 20:
            return 5
        elif avg_length > 10:
            return 3
        else:
            return 1
    
    def _calculate_confidence_scores(self, df: pd.DataFrame, mappings: Dict) -> Dict:
        """Calculate confidence scores for each mapping."""
        confidence_scores = {}
        
        for col_type, col_name in mappings.items():
            if col_name is None:
                continue
            
            score = 0
            col_name_lower = col_name.lower()
            
            # Name matching confidence
            if col_type in self.column_patterns:
                name_matches = [p for p in self.column_patterns[col_type] if p in col_name_lower]
                if name_matches:
                    # Exact match gets 100% name confidence
                    if any(p == col_name_lower for p in name_matches):
                        score += 40
                    else:
                        score += 30
                else:
                    score += 10  # Content-based mapping
            
            # Content validation confidence
            series = df[col_name]
            if col_type == 'date':
                if self._is_date_column(series.dropna().head(20)):
                    score += 40
                else:
                    score += 10
            elif col_type in ['amount', 'credit', 'debit', 'balance']:
                if self._is_numeric_column(series.dropna().head(20)):
                    score += 40
                else:
                    score += 10
            elif col_type == 'description':
                if self._is_text_column(series.dropna().head(20)):
                    score += 40
                else:
                    score += 10
            
            # Data completeness confidence
            completeness = series.notna().sum() / len(series)
            score += completeness * 20
            
            confidence_scores[col_type] = min(100, score)  # Cap at 100%
        
        return confidence_scores
    
    def _create_standardized_dataframe(self, df: pd.DataFrame, mappings: Dict) -> Optional[pd.DataFrame]:
        """Create a standardized DataFrame with mapped columns."""
        if not mappings.get('date') or not mappings.get('description'):
            return None  # Need at least date and description
        
        try:
            standardized_df = pd.DataFrame()
            
            # Map date column
            date_col = mappings['date']
            standardized_df['date'] = self._standardize_dates(df[date_col])
            
            # Map description column
            desc_col = mappings['description']
            standardized_df['description'] = df[desc_col].astype(str)
            
            # Handle amount columns
            if mappings.get('amount'):
                # Single amount column
                standardized_df['amount'] = self._standardize_amounts(df[mappings['amount']])
            elif mappings.get('credit') and mappings.get('debit'):
                # Separate credit/debit columns
                credit_amounts = self._standardize_amounts(df[mappings['credit']])
                debit_amounts = self._standardize_amounts(df[mappings['debit']])
                
                # Convert to single amount column (credit positive, debit negative)
                standardized_df['amount'] = credit_amounts.fillna(0) - debit_amounts.fillna(0)
            elif mappings.get('credit'):
                # Only credit column
                standardized_df['amount'] = self._standardize_amounts(df[mappings['credit']])
            elif mappings.get('debit'):
                # Only debit column (make negative)
                standardized_df['amount'] = -self._standardize_amounts(df[mappings['debit']])
            
            # Add balance if available
            if mappings.get('balance'):
                standardized_df['balance'] = self._standardize_amounts(df[mappings['balance']])
            
            # Add original columns for reference
            for col_type, col_name in mappings.items():
                if col_name not in ['date', 'description']:  # Don't duplicate
                    standardized_df[f'original_{col_type}'] = df[col_name]
            
            return standardized_df
            
        except Exception as e:
            print(f"Error creating standardized DataFrame: {e}")
            return None
    
    def _standardize_dates(self, date_series: pd.Series) -> pd.Series:
        """Standardize date column to datetime format."""
        standardized_dates = pd.Series(index=date_series.index, dtype='datetime64[ns]')
        
        for idx, date_value in date_series.items():
            if pd.isna(date_value):
                continue
            
            date_str = str(date_value)
            parsed_date = None
            
            # Try each date format
            for fmt in self.date_formats:
                try:
                    parsed_date = datetime.strptime(date_str[:19], fmt)
                    break
                except ValueError:
                    continue
            
            # If still not parsed, try pandas
            if parsed_date is None:
                try:
                    parsed_date = pd.to_datetime(date_str, errors='coerce')
                except:
                    pass
            
            standardized_dates.loc[idx] = parsed_date
        
        return standardized_dates
    
    def _standardize_amounts(self, amount_series: pd.Series) -> pd.Series:
        """Standardize amount column to numeric format."""
        # Remove common currency symbols and formatting
        cleaned_series = amount_series.astype(str).str.replace(r'[$,€£¥]', '', regex=True)
        cleaned_series = cleaned_series.str.replace(r'[()]', '', regex=True)  # Remove parentheses
        cleaned_series = cleaned_series.str.strip()
        
        # Convert to numeric
        numeric_series = pd.to_numeric(cleaned_series, errors='coerce')
        
        return numeric_series
    
    def _generate_mapping_suggestions(self, mappings: Dict, confidence_scores: Dict) -> List[str]:
        """Generate suggestions for improving mappings."""
        suggestions = []
        
        # Check for missing essential columns
        if not mappings.get('date'):
            suggestions.append("⚠️ No date column detected. Please ensure your CSV has a date column.")
        elif confidence_scores.get('date', 0) < 70:
            suggestions.append("⚠️ Date mapping has low confidence. Verify date format is correct.")
        
        if not mappings.get('description'):
            suggestions.append("⚠️ No description column detected. Transaction descriptions are important for analysis.")
        
        if not mappings.get('amount') and not (mappings.get('credit') and mappings.get('debit')):
            suggestions.append("⚠️ No amount column detected. Please ensure your CSV has transaction amounts.")
        
        # Check confidence scores
        for col_type, score in confidence_scores.items():
            if score < 50:
                suggestions.append(f"⚠️ Low confidence mapping for {col_type} column. Please verify.")
        
        return suggestions
    
    def _generate_mapping_warnings(self, df: pd.DataFrame, mappings: Dict) -> List[str]:
        """Generate warnings about potential data issues."""
        warnings = []
        
        # Check data completeness
        for col_type, col_name in mappings.items():
            if col_name:
                missing_pct = (df[col_name].isna().sum() / len(df)) * 100
                if missing_pct > 10:
                    warnings.append(f"⚠️ {col_name} column has {missing_pct:.1f}% missing values")
        
        # Check date range
        if mappings.get('date'):
            try:
                dates = self._standardize_dates(df[mappings['date']])
                date_range = dates.max() - dates.min()
                if date_range.days > 365 * 2:
                    warnings.append("⚠️ Date range spans more than 2 years. Large datasets may take longer to process.")
            except:
                warnings.append("⚠️ Unable to parse some dates. Some transactions may be excluded from analysis.")
        
        # Check for duplicate transactions
        if len(mappings) >= 2:
            try:
                subset_cols = [col for col in mappings.values() if col]
                duplicates = df.duplicated(subset=subset_cols).sum()
                if duplicates > 0:
                    warnings.append(f"⚠️ Found {duplicates} potential duplicate transactions")
            except:
                pass
        
        return warnings
    
    def get_mapping_summary(self, mappings: Dict, confidence_scores: Dict) -> str:
        """Generate a human-readable summary of the mapping results."""
        if not mappings:
            return "❌ Unable to map any columns automatically."
        
        summary_lines = ["✅ Column Mapping Results:"]
        
        for col_type, col_name in mappings.items():
            if col_name:
                confidence = confidence_scores.get(col_type, 0)
                confidence_icon = "🟢" if confidence > 70 else "🟡" if confidence > 50 else "🔴"
                summary_lines.append(f"  {confidence_icon} {col_type.title()}: '{col_name}' ({confidence:.0f}% confidence)")
        
        return "\n".join(summary_lines)
# --- Add this at the very bottom of column_mapper.py (outside the class) ---

def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Public helper function to use ColumnMapper and return a standardized DataFrame.
    Raises error if mapping is not successful.
    """
    mapper = ColumnMapper()
    result = mapper.auto_map_columns(df)

    if not result["success"]:
        raise ValueError("Column mapping failed:\\n" + "\\n".join(result.get("suggestions", [])))

    return result["standardized_df"]



   