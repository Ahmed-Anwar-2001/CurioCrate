from django import forms

# Choices for the user to select which type of data they are uploading
MODEL_CHOICES = [
    ('links', 'Trustpilot Basic Links (trustpilot_card_links_aggregated.csv)'),
    ('business', 'Trustpilot Detailed Business Data (trustpilot_business_data.csv)'),
]

class CSVUploadForm(forms.Form):
    model_type = forms.ChoiceField(
        choices=MODEL_CHOICES,
        label="Select the type of data you are uploading",
        widget=forms.RadioSelect,  # Radio buttons are user-friendly for few options
        required=True
    )
    csv_file = forms.FileField(
        label="Select your CSV file",
        required=True,
        widget=forms.ClearableFileInput(attrs={'accept': '.csv'})
    )

    # Add validation to ensure the uploaded file is a CSV
    def clean_csv_file(self):
        file = self.cleaned_data.get('csv_file')
        if file:
            if not file.name.endswith('.csv'):
                raise forms.ValidationError("Please upload a valid .csv file.")
        return file
