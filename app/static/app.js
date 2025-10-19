document.addEventListener('DOMContentLoaded', () => {
  const addressInput = document.getElementById('address');
  const suburbSelect = document.getElementById('suburb');
  const bedroomsInput = document.getElementById('bedrooms');
  const bathroomsInput = document.getElementById('bathrooms');
  const parkingInput = document.getElementById('parking');
  const landSizeInput = document.getElementById('land_size');

  async function lookupProperty(address) {
    if (!address) {
      return;
    }
    try {
      const response = await fetch(`/api/property-info?address=${encodeURIComponent(address)}`);
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      populateFromRecord(data);
    } catch (error) {
      console.warn('Unable to fetch property info', error);
    }
  }

  function populateFromRecord(record) {
    if (!record) return;
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
  addressInput.addEventListener('input', () => {
    clearTimeout(fetchTimeout);
    fetchTimeout = setTimeout(() => {
      lookupProperty(addressInput.value.trim());
    }, 400);
  });

  addressInput.addEventListener('change', () => {
    lookupProperty(addressInput.value.trim());
  });
});
