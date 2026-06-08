CREATE OR REPLACE FUNCTION public.clean_old_access_images()
RETURNS void AS $$
BEGIN

  DELETE FROM storage.objects
  WHERE bucket_id = 'access-images'
    AND created_at < (now() - INTERVAL '30 days');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.trg_func_clean_old_images()
RETURNS trigger AS $$
BEGIN
  PERFORM public.clean_old_access_images();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_clean_old_images ON public.accesos;

CREATE TRIGGER trg_clean_old_images
AFTER INSERT ON public.accesos
FOR EACH STATEMENT
EXECUTE FUNCTION public.trg_func_clean_old_images();
