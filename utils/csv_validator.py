import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re


class CSVValidator:
    """Validates CSV structure and data quality for financial transaction processing."""
    
    def __init__(self):
        # Common date formats found in bank exports
        self.date_formats = [
            '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y',
            '%Y/%m/%d', '%d-%b-%y', '%d-%b-%Y', '%b-%d-%Y', '%Y-%m-%d %H:%M:%S'
        ]
        
        # Minimum data requirements
        self.min_transactions = 5
        self.max_file_size_mb = 500
        
    def validate_csv_file(self, file_path: str) -> Dict:
            """
            Comprehensive CSV validation.
            
            Returns:
                dict: Validation results with success status, errors, warnings, and metadata
            """
            result = {
                'success': False,
                'errors': [],
                'warnings': [],
                'metadata': {},
                'suggestions': []
            }
            print("validate_csv_file:::", file_path)
            
            try:
                # Step 1: Basic file validation
                file_validation = self._validate_file_basics(file_path)
                print(file_validation)
                if not file_validation['success']:
                    result['errors'].extend(file_validation['errors'])
                    return result
                
                # Step 2: Load and parse CSV
                df_result = self._load_csv_safely(file_path)
                if not df_result['success']:
                    result['errors'].extend(df_result['errors'])
                    return result
                
                df = df_result['dataframe']
                print("Df",df)
                result['metadata']['row_count'] = len(df)
                result['metadata']['column_count'] = len(df.columns)
                result['metadata']['columns'] = list(df.columns)
                
                # Step 3: Structure validation
                structure_validation = self._validate_structure(df)
                print(" structure_validation", structure_validation)
                result['errors'].extend(structure_validation['errors'])
                result['warnings'].extend(structure_validation['warnings'])
                result['metadata'].update(structure_validation['metadata'])
                
                # Step 4: Data quality validation
                quality_validation = self._validate_data_quality(df)
                print("quality_validation",quality_validation)
                result['errors'].extend(quality_validation['errors'])
                result['warnings'].extend(quality_validation['warnings'])
                result['metadata'].update(quality_validation['metadata'])
                
                # Step 5: Generate suggestions
                result['suggestions'] = self._generate_suggestions(result)
                print("result:",result)
                # Overall success determination
                result['success'] = len(result['errors']) == 0

                result['dataframe']=df_result['dataframe']
                print("1234 RESULTS:",result)
                
                return result
                
            except Exception as e:
                result['errors'].append(f"Unexpected error during validation: {str(e)}")
                return result
    
    def _validate_file_basics(self, file_path: str) -> Dict:
        """Basic file size and accessibility checks."""
        import os
        
        try:
            if not os.path.exists(file_path):
                return {'success': False, 'errors': ['File not found']}
            
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                return {
                    'success': False, 
                    'errors': [f'File too large ({file_size_mb:.1f}MB). Maximum allowed: {self.max_file_size_mb}MB']
                }
            
            return {'success': True, 'errors': []}
            
        except Exception as e:
            return {'success': False, 'errors': [f'Error accessing file: {str(e)}']}
    
    def _load_csv_safely(self, file_path: str) -> Dict:
        """Attempt to load CSV with different encodings and separators."""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        separators = [',', ';', '\t', '|']
        
        for encoding in encodings:
            for sep in separators:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, sep=sep, 
                                   low_memory=False, skipinitialspace=True)
                    
                    # Basic sanity check - should have at least 2 columns and 1 row
                    if len(df.columns) >= 2 and len(df) >= 1:
                        return {
                            'success': True,
                            'dataframe': df,
                            'encoding': encoding,
                            'separator': sep
                        }
                        
                except Exception:
                    continue
        
        return {
            'success': False,
            'errors': ['Could not parse CSV file. Please check format and encoding.']
        }
    
    def _validate_structure(self, df: pd.DataFrame) -> Dict:
        """Validate CSV structure for required financial data columns."""
        errors = []
        warnings = []
        metadata = {}
        
        # Check minimum row count
        if len(df) < self.min_transactions:
            errors.append(f'Too few transactions ({len(df)}). Minimum required: {self.min_transactions}')
        
        # Check for completely empty DataFrame
        if df.empty:
            errors.append('CSV file is empty')
            return {'errors': errors, 'warnings': warnings, 'metadata': metadata}
        
        # Identify potential date columns
        date_columns = self._identify_date_columns(df)
        metadata['potential_date_columns'] = date_columns
        
        if not date_columns:
            errors.append('No date column found. Please ensure your CSV has a date column.')
        
        # Identify potential amount columns
        amount_columns = self._identify_amount_columns(df)
        metadata['potential_amount_columns'] = amount_columns
        
        if not amount_columns:
            errors.append('No amount column found. Please ensure your CSV has transaction amounts.')
        
        # Identify description columns
        description_columns = self._identify_description_columns(df)
        metadata['potential_description_columns'] = description_columns
        
        # Check for duplicate headers
        if len(df.columns) != len(set(df.columns)):
            warnings.append('Duplicate column names detected')
        
        # Check for unnamed columns
        unnamed_cols = [col for col in df.columns if 'Unnamed' in str(col)]
        if unnamed_cols:
            warnings.append(f'Found {len(unnamed_cols)} unnamed columns')
        
        return {'errors': errors, 'warnings': warnings, 'metadata': metadata}
    
    def _validate_data_quality(self, df: pd.DataFrame) -> Dict:
        """Validate data quality within the CSV."""
        errors = []
        warnings = []
        metadata = {}
        
        # Check for completely empty rows
        empty_rows = df.isnull().all(axis=1).sum()
        if empty_rows > 0:
            warnings.append(f'{empty_rows} completely empty rows found')
        
        # Calculate overall missing data percentage
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        missing_percentage = (missing_cells / total_cells) * 100
        metadata['missing_data_percentage'] = round(missing_percentage, 2)
        
        if missing_percentage > 50:
            errors.append(f'Too much missing data ({missing_percentage:.1f}%)')
        elif missing_percentage > 20:
            warnings.append(f'High amount of missing data ({missing_percentage:.1f}%)')
        
        # Check each column for data quality issues
        for col in df.columns:
            col_missing = df[col].isnull().sum()
            col_missing_pct = (col_missing / len(df)) * 100
            
            if col_missing_pct > 80:
                warnings.append(f'Column "{col}" is mostly empty ({col_missing_pct:.1f}%)')
        
        return {'errors': errors, 'warnings': warnings, 'metadata': metadata}
    
    def _identify_date_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns that likely contain dates."""
        date_columns = []
        
        for col in df.columns:
            col_name_lower = str(col).lower()
            
            # Check column name patterns
            if any(keyword in col_name_lower for keyword in 
                   ['date', 'time', 'posted', 'transaction', 'effective']):
                date_columns.append(col)
                continue
            
            # Check data patterns in first few non-null values
            sample_values = df[col].dropna().head(10)
            if len(sample_values) == 0:
                continue
            
            date_like_count = 0
            for value in sample_values:
                if self._looks_like_date(str(value)):
                    date_like_count += 1
            
            # If more than 70% of sample values look like dates
            if date_like_count / len(sample_values) > 0.7:
                date_columns.append(col)
        
        return date_columns
    
    def _identify_amount_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns that likely contain monetary amounts."""
        amount_columns = []
        
        for col in df.columns:
            col_name_lower = str(col).lower()
            
            # Check column name patterns
            if any(keyword in col_name_lower for keyword in 
                   ['amount', 'balance', 'credit', 'debit', 'transaction', 'value', 'sum']):
                # Verify it contains numeric data
                if self._is_numeric_column(df[col]):
                    amount_columns.append(col)
                continue
            
            # Check if column contains numeric data that could be amounts
            if self._is_numeric_column(df[col]):
                # Additional checks for monetary patterns
                sample_values = df[col].dropna().head(20)
                if len(sample_values) > 0:
                    # Check for typical monetary value ranges and patterns
                    numeric_values = pd.to_numeric(sample_values, errors='coerce')
                    if numeric_values.notna().sum() > len(sample_values) * 0.8:
                        amount_columns.append(col)
        
        return amount_columns
    
    def _identify_description_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns that likely contain transaction descriptions."""
        description_columns = []
        
        for col in df.columns:
            col_name_lower = str(col).lower()
            
            # Check column name patterns
            if any(keyword in col_name_lower for keyword in 
                   ['description', 'memo', 'reference', 'details', 'payee', 'merchant', 'note']):
                description_columns.append(col)
                continue
            
            # Check if column contains text data
            if df[col].dtype == 'object':  # String/text column
                sample_values = df[col].dropna().head(10)
                if len(sample_values) > 0:
                    # Check average text length (descriptions usually longer than codes)
                    avg_length = sample_values.astype(str).str.len().mean()
                    if avg_length > 10:  # Arbitrary threshold for meaningful descriptions
                        description_columns.append(col)
        
        return description_columns
    
    def _looks_like_date(self, value: str) -> bool:
        """Check if a string value looks like a date."""
        # Try to parse with common date formats
        for fmt in self.date_formats:
            try:
                datetime.strptime(str(value)[:19], fmt)  # Limit to avoid microsecond issues
                return True
            except ValueError:
                continue
        
        # Check for date-like patterns with regex
        date_patterns = [
            r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
            r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'\d{1,2}-\d{1,2}-\d{4}',  # MM-DD-YYYY or DD-MM-YYYY
            r'\d{1,2}-\w{3}-\d{2,4}',  # DD-MMM-YY or DD-MMM-YYYY
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, str(value)):
                return True
        
        return False
    
    def _is_numeric_column(self, series: pd.Series) -> bool:
        """Check if a pandas Series contains primarily numeric data."""
        # Try to convert to numeric
        numeric_series = pd.to_numeric(series, errors='coerce')
        
        # Check what percentage of non-null values are numeric
        non_null_count = series.notna().sum()
        if non_null_count == 0:
            return False
        
        numeric_count = numeric_series.notna().sum()
        numeric_percentage = numeric_count / non_null_count
        
        return numeric_percentage > 0.7  # 70% threshold
    
    def _generate_suggestions(self, result: Dict) -> List[str]:
        """Generate helpful suggestions based on validation results."""
        suggestions = []
        
        if not result['success']:
            suggestions.append("💡 Make sure your CSV has columns for: Date, Amount, and Description")
        
        if 'potential_date_columns' in result['metadata']:
            if not result['metadata']['potential_date_columns']:
                suggestions.append("📅 Add a date column with format like: 2025-01-15 or 01/15/2025")
        
        if 'potential_amount_columns' in result['metadata']:
            if not result['metadata']['potential_amount_columns']:
                suggestions.append("💰 Add an amount column with numeric values (e.g., 150.50, -25.00)")
        
        if 'missing_data_percentage' in result['metadata']:
            if result['metadata']['missing_data_percentage'] > 10:
                suggestions.append("🔍 Try to fill in missing data for better analysis accuracy")
        
        return suggestions


# Helper function for easy import
def get_csv_validator() -> CSVValidator:
    """Get a configured CSVValidator instance."""
    return CSVValidator()

def validate_csv(file_path: str) -> pd.DataFrame:
    """
    Shortcut function to validate and return cleaned DataFrame, or raise error.
    """
    validator = get_csv_validator()
    result = validator.validate_csv_file(file_path)

    print("Final_RESULTS",result)

    if not result["success"]:
        error_list = result["errors"] + result.get("suggestions", [])
        raise ValueError("CSV validation failed:\\n" + "\\n".join(error_list))

    return result["dataframe"]
