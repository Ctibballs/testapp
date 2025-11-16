const { useState, useEffect, useMemo, useCallback, useRef } = React;

const currencyFormatter = new Intl.NumberFormat('en-AU', {
  style: 'currency',
  currency: 'AUD',
  maximumFractionDigits: 0,
});

const defaultAddress = () => ({
  fullAddress: '',
  suburb: '',
  state: '',
  postcode: '',
  lat: null,
  lng: null,
});

const defaultDetails = () => ({
  propertyType: 'house',
  bedrooms: '',
  landSize: '',
});

const defaultOptions = () => ({
  emailEstimate: false,
  connectToAgent: false,
});

const defaultContact = () => ({
  userName: '',
  userEmail: '',
  userPhone: '',
});

function formatCurrency(value) {
  if (!value && value !== 0) return '—';
  return currencyFormatter.format(value);
}

function StepIndicator({ step }) {
  return (
    <div className="step-indicator" aria-label={`Step ${step} of 3`}>
      {[1, 2, 3].map((idx) => (
        <div key={idx} className={`step-dot ${idx <= step ? 'active' : ''}`}></div>
      ))}
    </div>
  );
}

function parsePlace(place) {
  if (!place || !place.address_components) return null;
  const findComponent = (type) => {
    const component = place.address_components.find((item) => item.types.includes(type));
    return component ? component.long_name : '';
  };
  return {
    fullAddress: place.formatted_address || '',
    suburb: findComponent('locality') || findComponent('postal_town') || '',
    state: findComponent('administrative_area_level_1') || '',
    postcode: findComponent('postal_code') || '',
    lat: place.geometry?.location?.lat?.() ?? null,
    lng: place.geometry?.location?.lng?.() ?? null,
  };
}

function usePlacesAutocomplete(isActive, onSelect) {
  const inputRef = useRef(null);
  useEffect(() => {
    if (!isActive || !inputRef.current) return;
    if (!(window.google && window.google.maps && window.google.maps.places)) return;
    const autocomplete = new window.google.maps.places.Autocomplete(inputRef.current, {
      componentRestrictions: { country: 'au' },
      fields: ['formatted_address', 'address_components', 'geometry'],
      types: ['address'],
    });
    const listener = autocomplete.addListener('place_changed', () => {
      const place = autocomplete.getPlace();
      const parsed = parsePlace(place);
      if (parsed) {
        onSelect(parsed);
      }
    });
    return () => {
      window.google.maps.event.clearInstanceListeners(autocomplete);
      listener?.remove?.();
    };
  }, [isActive, onSelect]);
  return inputRef;
}

function QuietEstimateApp() {
  const [isWidgetOpen, setWidgetOpen] = useState(false);
  const [step, setStep] = useState(1);
  const [address, setAddress] = useState(defaultAddress);
  const [details, setDetails] = useState(defaultDetails);
  const [options, setOptions] = useState(defaultOptions);
  const [contact, setContact] = useState(defaultContact);
  const [estimate, setEstimate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [leadError, setLeadError] = useState('');

  const resetState = () => {
    setStep(1);
    setAddress(defaultAddress());
    setDetails(defaultDetails());
    setOptions(defaultOptions());
    setContact(defaultContact());
    setEstimate(null);
    setError('');
    setLeadError('');
  };

  const openWidget = () => {
    resetState();
    setWidgetOpen(true);
  };

  const closeWidget = () => {
    setWidgetOpen(false);
  };

  const handleManualAddressChange = (event) => {
    const value = event.target.value;
    setAddress((prev) => ({ ...prev, fullAddress: value }));
  };

  const handleAddressDetailsChange = (field, value) => {
    setAddress((prev) => ({ ...prev, [field]: value }));
  };

  const handleDetailsChange = (field, value) => {
    setDetails((prev) => ({ ...prev, [field]: value }));
  };

  const handleOptionsChange = (field, checked) => {
    setOptions((prev) => ({ ...prev, [field]: checked }));
    if (!checked) {
      setLeadError('');
    }
  };

  const handleContactChange = (field, value) => {
    setContact((prev) => ({ ...prev, [field]: value }));
  };

  const isGoogleReady = Boolean(window.google && window.google.maps && window.google.maps.places);
  const addressInputRef = usePlacesAutocomplete(isWidgetOpen && step === 1, (parsed) => {
    setAddress((prev) => ({ ...prev, ...parsed }));
  });

  const addressComplete = useMemo(() => {
    const fields = ['fullAddress', 'suburb', 'state', 'postcode'];
    return fields.every((field) => {
      const value = address[field];
      return typeof value === 'number' ? true : Boolean(value && String(value).trim());
    });
  }, [address]);

  const requestSignature = useMemo(() => {
    return JSON.stringify({
      fullAddress: address.fullAddress,
      suburb: address.suburb,
      state: address.state,
      postcode: address.postcode,
      propertyType: details.propertyType,
      bedrooms: details.bedrooms,
      landSize: details.landSize,
    });
  }, [address, details]);

  useEffect(() => {
    if (!isWidgetOpen || step !== 3 || !addressComplete) {
      return;
    }
    setError('');
    setLoading(true);
    setEstimate(null);
    const controller = new AbortController();
    const body = {
      ...address,
      propertyType: details.propertyType,
      bedrooms: details.bedrooms ? Number(details.bedrooms) : undefined,
      landSize: details.landSize ? Number(details.landSize) : undefined,
    };
    fetch('/api/estimate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.error || 'Unable to fetch estimate');
        }
        return response.json();
      })
      .then((data) => {
        setEstimate(data);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        setError(err.message);
        setLoading(false);
      });
    return () => controller.abort();
  }, [isWidgetOpen, step, addressComplete, requestSignature]);

  const goBack = () => {
    if (step === 1) {
      closeWidget();
    } else {
      setStep((prev) => Math.max(prev - 1, 1));
    }
  };

  const goNext = () => {
    if (step === 3) return;
    if (step === 1 && !addressComplete) return;
    setStep((prev) => Math.min(prev + 1, 3));
  };

  const submitLeadIfNeeded = useCallback(async () => {
    if (!estimate) return;
    if (!options.emailEstimate && !options.connectToAgent) return;
    const requireEmail = options.emailEstimate;
    const requireContact = options.connectToAgent;
    if (requireEmail && !contact.userEmail) {
      setLeadError('Please add an email so we can send the estimate.');
      return Promise.reject(new Error('Missing email'));
    }
    if (requireContact && !contact.userEmail && !contact.userPhone) {
      setLeadError('Add at least an email or phone so an agent can respond.');
      return Promise.reject(new Error('Missing contact details'));
    }

    const payload = {
      ...address,
      propertyType: details.propertyType,
      bedrooms: details.bedrooms ? Number(details.bedrooms) : undefined,
      landSize: details.landSize ? Number(details.landSize) : undefined,
      ...estimate,
      emailEstimate: options.emailEstimate,
      connectToAgent: options.connectToAgent,
      userName: contact.userName,
      userEmail: contact.userEmail,
      userPhone: contact.userPhone,
    };
    try {
      const response = await fetch('/api/leads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setLeadError(data.error || 'Unable to submit request.');
        return Promise.reject(new Error(data.error || 'Lead error'));
      }
      setLeadError('');
      return response.json();
    } catch (err) {
      setLeadError('Something went wrong while sending your preferences.');
      return Promise.reject(err);
    }
  }, [estimate, options, contact, address, details]);

  const finishFlow = async () => {
    if (options.emailEstimate || options.connectToAgent) {
      try {
        await submitLeadIfNeeded();
      } catch (error) {
        return;
      }
    }
    closeWidget();
  };

  return (
    <>
      <main>
        <section className="hero">
          <div className="hero-content">
            <p className="trust-badge">QuietEstimate</p>
            <h1>Check your home’s value with a calm, guided experience.</h1>
            <p>Three gentle steps to an instant, data-backed estimate. No agents calling unless you ask.</p>
            <button className="primary-cta" onClick={openWidget}>Get my free estimate</button>
            <div className="trust-badges" aria-label="Trust badges">
              <span className="trust-badge">Privacy-first</span>
              <span className="trust-badge">Powered by suburb medians</span>
            </div>
          </div>
          <div className="preview-card">
            <h3>What you’ll receive</h3>
            <p>A personalised value range plus suburb context delivered in under 30 seconds.</p>
            <div className="preview-range">
              <strong>$1.15m – $1.28m</strong>
              <span>Confidence: Medium</span>
            </div>
            <div className="preview-meta">
              <span>Suburb median: $1.20m</span>
              <span>Updated weekly</span>
            </div>
          </div>
        </section>
        <section className="highlights">
          <article className="highlight-card">
            <h4>Three steps</h4>
            <p>Address, a few optional details and you’re done.</p>
          </article>
          <article className="highlight-card">
            <h4>No pressure</h4>
            <p>See the estimate instantly. Opt in to email or agent help only if it suits you.</p>
          </article>
          <article className="highlight-card">
            <h4>Local context</h4>
            <p>We surface suburb medians and sales volumes so you can gauge confidence.</p>
          </article>
        </section>
      </main>

      {isWidgetOpen && (
        <div className="widget-overlay" role="dialog" aria-modal="true">
          <div className="widget-panel">
            <div className="widget-header">
              <div>
                <p style={{ margin: 0, color: '#64748b', fontWeight: 500 }}>QuietEstimate</p>
                <h2 style={{ margin: 0 }}>Let’s get your estimate</h2>
              </div>
              <button className="close-btn" onClick={closeWidget} aria-label="Close">×</button>
            </div>
            <StepIndicator step={step} />

            {step === 1 && (
              <div className="form-stack">
                <div>
                  <label htmlFor="addressInput">Property address</label>
                  <input
                    id="addressInput"
                    ref={addressInputRef}
                    type="text"
                    placeholder="Start typing your Australian address"
                    value={address.fullAddress}
                    onChange={handleManualAddressChange}
                  />
                  {!isGoogleReady && (
                    <small style={{ color: '#475569' }}>
                      Google Places isn’t connected in this demo, so enter suburb, state and postcode manually below.
                    </small>
                  )}
                </div>
                <div className="inline-inputs">
                  <div>
                    <label htmlFor="suburbInput">Suburb</label>
                    <input
                      id="suburbInput"
                      type="text"
                      value={address.suburb}
                      onChange={(event) => handleAddressDetailsChange('suburb', event.target.value)}
                    />
                  </div>
                  <div>
                    <label htmlFor="stateInput">State</label>
                    <input
                      id="stateInput"
                      type="text"
                      value={address.state}
                      onChange={(event) => handleAddressDetailsChange('state', event.target.value)}
                    />
                  </div>
                  <div>
                    <label htmlFor="postcodeInput">Postcode</label>
                    <input
                      id="postcodeInput"
                      type="text"
                      value={address.postcode}
                      onChange={(event) => handleAddressDetailsChange('postcode', event.target.value)}
                    />
                  </div>
                </div>
                <div className="widget-actions">
                  <button className="secondary-button" onClick={closeWidget}>Cancel</button>
                  <button className="widget-button" onClick={goNext} disabled={!addressComplete}>
                    Next
                  </button>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="form-stack">
                <div>
                  <label>Property type</label>
                  <div className="radio-group">
                    {['house', 'unit'].map((type) => (
                      <button
                        key={type}
                        type="button"
                        className={`pill-option ${details.propertyType === type ? 'active' : ''}`}
                        onClick={() => handleDetailsChange('propertyType', type)}
                      >
                        {type === 'house' ? 'House' : 'Unit / apartment'}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="inline-inputs">
                  <div>
                    <label htmlFor="bedroomsInput">Bedrooms (optional)</label>
                    <input
                      id="bedroomsInput"
                      type="number"
                      min="0"
                      value={details.bedrooms}
                      onChange={(event) => handleDetailsChange('bedrooms', event.target.value)}
                    />
                  </div>
                  <div>
                    <label htmlFor="landSizeInput">Land size m² (optional)</label>
                    <input
                      id="landSizeInput"
                      type="number"
                      min="0"
                      value={details.landSize}
                      onChange={(event) => handleDetailsChange('landSize', event.target.value)}
                    />
                  </div>
                </div>
                <div className="widget-actions">
                  <button className="secondary-button" onClick={goBack}>Back</button>
                  <button className="widget-button" onClick={goNext}>Next</button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="form-stack">
                {loading && (
                  <div>
                    <div className="spinner" aria-label="Loading estimate" />
                  </div>
                )}
                {error && <div className="error-box">{error}</div>}
                {estimate && !loading && (
                  <div className="estimate-panel">
                    <p style={{ margin: 0, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.85rem' }}>
                      Estimated range
                    </p>
                    <div className="estimate-range">
                      {formatCurrency(estimate.estimateLow)} – {formatCurrency(estimate.estimateHigh)}
                    </div>
                    <div className="estimate-meta">
                      <span>Confidence: {estimate.confidence}</span>
                      <span>
                        Suburb median {details.propertyType === 'house' ? 'house' : 'unit'} price:{' '}
                        {formatCurrency(
                          details.propertyType === 'house'
                            ? estimate.suburbStats.medianHousePrice
                            : estimate.suburbStats.medianUnitPrice
                        )}
                      </span>
                      <span>
                        Recent sales volume:{' '}
                        {details.propertyType === 'house'
                          ? estimate.suburbStats.numHouseSales12m
                          : estimate.suburbStats.numUnitSales12m}
                      </span>
                    </div>
                  </div>
                )}

                <div className="checkbox-group">
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={options.emailEstimate}
                      onChange={(event) => handleOptionsChange('emailEstimate', event.target.checked)}
                    />
                    <span>Email this estimate to me</span>
                  </label>
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={options.connectToAgent}
                      onChange={(event) => handleOptionsChange('connectToAgent', event.target.checked)}
                    />
                    <span>Introduce me to a calm local agent</span>
                  </label>
                </div>

                {(options.emailEstimate || options.connectToAgent) && (
                  <div className="inline-inputs">
                    <div>
                      <label htmlFor="nameInput">Name (optional)</label>
                      <input
                        id="nameInput"
                        type="text"
                        value={contact.userName}
                        onChange={(event) => handleContactChange('userName', event.target.value)}
                      />
                    </div>
                    <div>
                      <label htmlFor="emailInput">Email</label>
                      <input
                        id="emailInput"
                        type="email"
                        value={contact.userEmail}
                        onChange={(event) => handleContactChange('userEmail', event.target.value)}
                      />
                    </div>
                    <div>
                      <label htmlFor="phoneInput">Phone (optional)</label>
                      <input
                        id="phoneInput"
                        type="tel"
                        value={contact.userPhone}
                        onChange={(event) => handleContactChange('userPhone', event.target.value)}
                      />
                    </div>
                  </div>
                )}

                {leadError && <div className="error-box">{leadError}</div>}

                <p className="disclaimer">
                  Estimates are price guides only and not formal valuations. Contact details are only shared if you opt in.
                </p>

                <div className="widget-actions">
                  <button className="secondary-button" onClick={goBack}>Back</button>
                  <button className="widget-button" onClick={finishFlow} disabled={loading}>
                    {options.emailEstimate || options.connectToAgent ? 'Send & close' : 'Done'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<QuietEstimateApp />);
