document.addEventListener('DOMContentLoaded', () => {
  const addressInput = document.getElementById('address');
  const addressOptions = document.getElementById('address-options');
  const suburbSelect = document.getElementById('suburb');
  const bedroomsInput = document.getElementById('bedrooms');
  const bathroomsInput = document.getElementById('bathrooms');
  const parkingInput = document.getElementById('parking');
  const landSizeInput = document.getElementById('land_size');

  function splitAddress(value) {
    if (!value) {
      return { address: '', suburb: '' };
    }
    const [addressPart, ...suburbParts] = value.split(',');
    const suburb = suburbParts.join(',').trim();
    return { address: addressPart.trim(), suburb };
  }

  async function lookupProperty(value) {
    const { address, suburb } = splitAddress(value);
    if (!address) {
      return;
    }
    const params = new URLSearchParams({ address });
    if (suburb) {
      params.set('suburb', suburb);
    }
    try {
      const response = await fetch(`/api/property-info?${params.toString()}`);
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      populateFromRecord(data);
    } catch (error) {
      console.warn('Unable to fetch property info', error);
    }
  }

  async function fetchAddressSuggestions(value) {
    const query = value.trim();
    if (query.length < 3) {
      addressOptions.innerHTML = '';
      return;
    }
    try {
      const response = await fetch(`/api/properties?q=${encodeURIComponent(query)}`);
      if (!response.ok) {
        return;
      }
      const suggestions = await response.json();
      addressOptions.innerHTML = '';
      suggestions.forEach((suggestion) => {
        const option = document.createElement('option');
        option.value = `${suggestion.address}, ${suggestion.suburb}`;
        addressOptions.appendChild(option);
      });
    } catch (error) {
      console.warn('Unable to fetch address suggestions', error);
    }
  }

  function populateFromRecord(record) {
    if (!record) return;
    if (record.address && record.suburb) {
      addressInput.value = `${record.address}, ${record.suburb}`;
    }
    if (record.suburb) {
      const option = Array.from(suburbSelect.options).find((opt) => opt.value === record.suburb);
      if (option) {
        suburbSelect.value = record.suburb;
      }
    }
    if (record.bedrooms != null && record.bedrooms !== '') {
      bedroomsInput.value = record.bedrooms;
    }
    if (record.bathrooms != null && record.bathrooms !== '') {
      bathroomsInput.value = record.bathrooms;
    }
    if (record.parking != null && record.parking !== '') {
      parkingInput.value = record.parking;
    }
    if (record.land_size != null && record.land_size !== '') {
      landSizeInput.value = record.land_size;
    }
  }

  let fetchTimeout;
  addressInput.addEventListener('input', (event) => {
    const value = event.target.value;
    fetchAddressSuggestions(value);
    clearTimeout(fetchTimeout);
    fetchTimeout = setTimeout(() => {
      lookupProperty(value.trim());
    }, 400);
  });

  addressInput.addEventListener('change', (event) => {
    lookupProperty(event.target.value.trim());
  });
});
