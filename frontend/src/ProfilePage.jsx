import {useState} from 'react';
import {Check} from 'lucide-react';
import {api} from './api';

export function ProfileAvatar({user}) {
  return user.photo_url
    ? <img className="avatar" src={user.photo_url} alt="Foto de perfil"/>
    : <span className="avatar" aria-hidden="true">{user.first_name?.[0]}{user.last_name?.[0]}</span>;
}

export default function ProfilePage({user, onUpdate, onReauthenticate, Field, Button, PageHeader}) {
  const [firstName, setFirstName] = useState(user.first_name || '');
  const [lastName, setLastName] = useState(user.last_name || '');
  const [email, setEmail] = useState(user.email || '');
  const [emailPassword, setEmailPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [phonePassword, setPhonePassword] = useState('');
  const [challengeId, setChallengeId] = useState('');
  const [code, setCode] = useState('');
  const [photo, setPhoto] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const changingEmail = email.trim().toLowerCase() !== (user.email || '').toLowerCase();

  async function run(section, work) {
    setBusy(true);
    setNotice(null);
    try {
      const message = await work();
      if (message) setNotice({section, message});
    } catch (error) {
      setNotice({section, message:error.message, error:true});
    } finally {
      setBusy(false);
    }
  }

  function feedback(section) {
    if (notice?.section !== section) return null;
    return <p role={notice.error ? 'alert' : 'status'} className={notice.error ? 'form-error' : 'green-text'}>{notice.message}</p>;
  }

  function saveDetails(event) {
    event.preventDefault();
    return run('details', async () => {
      const updated = await api('auth/me/', {method:'PATCH', body:{
        first_name:firstName, last_name:lastName, email, current_password:emailPassword,
      }});
      onUpdate(updated);
      setEmail(updated.email);
      setEmailPassword('');
      return 'Datos guardados.';
    });
  }

  function savePhoto(event) {
    event.preventDefault();
    const form = event.currentTarget;
    return run('photo', async () => {
      const body = new FormData();
      body.append('photo', photo);
      onUpdate(await api('auth/me/photo/', {method:'PUT', body}));
      form.reset();
      setPhoto(null);
      return 'Foto actualizada.';
    });
  }

  function updatePhone(event) {
    event.preventDefault();
    return run('phone', async () => {
      if (!challengeId) {
        const result = await api('auth/me/phone/', {method:'POST', body:{phone, current_password:phonePassword}});
        setChallengeId(result.challenge_id);
        setPhonePassword('');
        return 'Ingresa el código que enviamos al nuevo número.';
      }
      const result = await api('auth/me/phone/', {method:'PUT', body:{phone, challenge_id:challengeId, code}});
      onReauthenticate(result.detail);
    });
  }

  return <>
    <PageHeader title="Mi perfil"/>
    <div className="profile-grid">
      <form className="panel side-form" onSubmit={saveDetails}>
        <h2>Datos personales</h2>
        <div className="field-grid">
          <Field label="Nombre" value={firstName} onChange={event=>setFirstName(event.target.value)} maxLength={150} autoComplete="given-name"/>
          <Field label="Apellido" value={lastName} onChange={event=>setLastName(event.target.value)} maxLength={150} autoComplete="family-name"/>
        </div>
        <Field label="Correo electrónico" type="email" required value={email} onChange={event=>setEmail(event.target.value)} autoComplete="email"/>
        {changingEmail&&<Field label="Contraseña actual para cambiar el correo" type="password" required value={emailPassword} onChange={event=>setEmailPassword(event.target.value)} autoComplete="current-password"/>}
        <p className="input-help">{user.role_label}{user.role_label&&user.region?' · ':''}{user.region}</p>
        {feedback('details')}
        <div className="form-actions"><Button kind="primary" icon={Check} disabled={busy}>Guardar datos</Button></div>
      </form>
      <form className="panel side-form profile-photo-form" onSubmit={savePhoto}>
        <h2>Foto de perfil</h2>
        <ProfileAvatar user={user}/>
        <Field label="Seleccionar foto"><input type="file" accept="image/jpeg,image/png,image/webp" onChange={event=>setPhoto(event.target.files[0]||null)}/></Field>
        {feedback('photo')}
        <div className="form-actions">
          {user.photo_url&&<Button type="button" disabled={busy} onClick={()=>run('photo', async()=>{
            onUpdate(await api('auth/me/photo/', {method:'DELETE'}));
            return 'Foto eliminada.';
          })}>Quitar foto</Button>}
          <Button kind="primary" disabled={busy||!photo}>Guardar foto</Button>
        </div>
      </form>
      <form className="panel side-form" onSubmit={updatePhone}>
        <h2>Celular para SMS</h2>
        <p>Registrado: {user.phone || 'Sin celular registrado'}</p>
        <Field label="Nuevo celular" type="tel" placeholder="+56912345678" autoComplete="tel" required value={phone} onChange={event=>setPhone(event.target.value)} disabled={!!challengeId}/>
        {challengeId
          ? <Field label="Código SMS" required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={event=>setCode(event.target.value)}/>
          : <Field label="Contraseña actual para cambiar el celular" type="password" required autoComplete="current-password" value={phonePassword} onChange={event=>setPhonePassword(event.target.value)}/>}
        {feedback('phone')}
        <div className="form-actions">
          {challengeId&&<Button type="button" disabled={busy} onClick={()=>{setChallengeId('');setCode('');setNotice(null);}}>Volver</Button>}
          <Button kind="primary" disabled={busy}>{challengeId?'Confirmar celular':'Enviar código SMS'}</Button>
        </div>
      </form>
    </div>
  </>;
}
