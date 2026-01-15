#

Quote Request is incoming. It has the folloiwng (example) payload

```json
{
  'formId': '1n8keGTL84MKZYhKWhbZpD',
  'formTitle': 'Contract Logistics Quote Form',
  'formLocale': 'fr-FR',
  'commercialOwner': 'Transport & Logistics',
  'clientSessionId': '484253205.1755506045',
  'businessArea': 'FREIGHT_FERRIES_AND_LOGISTICS',
  'segmentId': '',
  'anonymousSegmentId': '6a7ab006-c10f-4712-af33-6ed8cf070574',
  'FirstName': 'Laurent',
  'LastName': 'Hugues',
  'CompanyName': 'Miranda',
  'CompanyEmail': 'laurent.f.hugues@gmail.com',
  'PhoneNumber': '+33625799745',
  'DescribeYourCargo': '1 cyclomoteur 50 cc',
  'ContractLogisticsService': 'ValueAddedServices',
  'userSegmentID': {'anonymousUserId': '6a7ab006-c10f-4712-af33-6ed8cf070574'},
  'formVariant': None,
  'referer': 'https://www.dfds.com/fr-fr/ferries-fret-et-logistique/contrat-logistique-devis',
  'queryParams': {}
}
```

# Observations

COMPANY LOCATION
The "dfds_fullpayload" does not seem to have "Comapny Location" (Country / City), even if this field is required in the form!? How can this be?

TIMESTAMPS
The "dfds_fullpayload" does not seem to any timestamps!? The lead record itself, has 3 timestamps. How are these generated?

createdon: 2025-08-18T08:56:33Z
dfds_lastactionon: 2025-08-19T08:44:03Z
modifiedon: 2025-08-19T08:44:03Z

# Lead Checks

EMAIL:

- "company" vs "free" email

PHONE NUMBER:

- adheres to phone number standards given the country

NAME:

- First Name and Last Name written "correctly"

ROUTE:

- Does it fit with existing routes
