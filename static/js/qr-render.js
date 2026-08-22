/* QR code renderer for 2FA pages */
document.addEventListener('DOMContentLoaded', function () {
  var qr = document.getElementById('qrcode');
  if (!qr || typeof QRCode === 'undefined') return;
  var uri = qr.dataset.uri;
  if (!uri) return;
  new QRCode(qr, {
    text: uri,
    width: 200,
    height: 200,
    colorDark: '#000000',
    colorLight: '#ffffff',
    correctLevel: QRCode.CorrectLevel.H,
  });
});
