import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { downloadBlob } from './downloadBlob.js';

describe('downloadBlob', () => {
  let createObjectURL;
  let revokeObjectURL;
  let clickSpy;

  beforeEach(() => {
    createObjectURL = vi.fn(() => 'blob:mock-url');
    revokeObjectURL = vi.fn();
    URL.createObjectURL = createObjectURL;
    URL.revokeObjectURL = revokeObjectURL;
    clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  });

  afterEach(() => {
    clickSpy.mockRestore();
  });

  it('creates an object URL for the blob and clicks a download link with the given filename', () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' });

    downloadBlob(blob, 'rapport-oracle-gerland.pdf');

    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(clickSpy).toHaveBeenCalledTimes(1);
  });

  it('revokes the object URL after triggering the download', () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' });

    downloadBlob(blob, 'rapport.pdf');

    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('does not leave the temporary link element in the document', () => {
    const blob = new Blob(['%PDF-1.4'], { type: 'application/pdf' });

    downloadBlob(blob, 'rapport.pdf');

    expect(document.querySelector('a[download="rapport.pdf"]')).toBeNull();
  });
});
