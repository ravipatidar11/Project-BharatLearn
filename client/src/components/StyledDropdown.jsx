import { useEffect, useId, useRef, useState } from 'react';
import { Check, ChevronDown } from 'lucide-react';

export function StyledDropdown({
  value,
  options,
  onChange,
  name,
  ariaLabel,
  leadingIcon,
  className = '',
  disabled = false,
}) {
  const id = useId();
  const rootRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [placement, setPlacement] = useState('below');
  const [alignRight, setAlignRight] = useState(false);
  const selectedIndex = options.findIndex(option => String(option.value) === String(value));
  const [activeIndex, setActiveIndex] = useState(Math.max(0, selectedIndex));
  const selected = selectedIndex >= 0 ? options[selectedIndex] : null;
  const menuId = `${id}-menu`;

  useEffect(() => {
    if (!open) return undefined;
    const closeIfOutside = event => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener('pointerdown', closeIfOutside);
    return () => document.removeEventListener('pointerdown', closeIfOutside);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    document.getElementById(`${id}-option-${activeIndex}`)?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex, id, open]);

  const showMenu = () => {
    if (!options.length) return;
    const bounds = rootRef.current?.getBoundingClientRect();
    if (bounds) {
      const menuHeight = Math.min(options.length * 39 + 14, Math.min(320, window.innerHeight * .45));
      setPlacement(window.innerHeight - bounds.bottom < menuHeight && bounds.top > menuHeight ? 'above' : 'below');
      setAlignRight(bounds.left + Math.max(bounds.width, 210) > window.innerWidth - 12);
    }
    setActiveIndex(Math.max(0, selectedIndex));
    setOpen(true);
  };

  const choose = option => {
    if (!option || option.disabled) return;
    onChange?.({ target: { name, value: String(option.value), type: 'select-one' } });
    setOpen(false);
  };

  const handleKeyDown = event => {
    if (event.key === 'Escape') {
      event.preventDefault();
      setOpen(false);
      return;
    }
    if (event.key === 'Tab') {
      setOpen(false);
      return;
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      if (!open) {
        showMenu();
        return;
      }
      const direction = event.key === 'ArrowDown' ? 1 : -1;
      setActiveIndex(index => (index + direction + options.length) % options.length);
      return;
    }
    if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault();
      setActiveIndex(event.key === 'Home' ? 0 : options.length - 1);
      setOpen(true);
      return;
    }
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (open) choose(options[activeIndex]);
      else showMenu();
    }
  };

  return (
    <div
      className={`styled-dropdown ${open ? 'styled-dropdown-open' : ''} ${className}`.trim()}
      ref={rootRef}
      onKeyDown={handleKeyDown}
    >
      <button
        type="button"
        className="styled-dropdown-trigger"
        role="combobox"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={menuId}
        aria-activedescendant={open ? `${id}-option-${activeIndex}` : undefined}
        disabled={disabled||!options.length}
        onClick={() => open ? setOpen(false) : showMenu()}
      >
        <span className="styled-dropdown-value">
          {leadingIcon&&<span className="styled-dropdown-leading">{leadingIcon}</span>}
          <span className="styled-dropdown-label">{selected?.label ?? ''}</span>
        </span>
        <ChevronDown className="styled-dropdown-chevron" size={15}/>
      </button>
      {open&&<div className={`styled-dropdown-menu ${placement==='above'?'opens-above':''} ${alignRight?'align-right':''}`} id={menuId} role="listbox" aria-label={ariaLabel}>
        {options.map((option, index) => {
          const isSelected = String(option.value) === String(value);
          const isActive = index === activeIndex;
          return <button
            key={`${option.value}-${index}`}
            type="button"
            id={`${id}-option-${index}`}
            role="option"
            aria-selected={isSelected}
            disabled={option.disabled}
            tabIndex={-1}
            className={`styled-dropdown-option ${isSelected ? 'is-selected' : ''} ${isActive ? 'is-active' : ''}`}
            onMouseDown={event=>event.preventDefault()}
            onMouseEnter={()=>setActiveIndex(index)}
            onClick={()=>choose(option)}
          >
            <span>{option.label}</span>
            {isSelected&&<Check size={15}/>}
          </button>;
        })}
      </div>}
    </div>
  );
}
