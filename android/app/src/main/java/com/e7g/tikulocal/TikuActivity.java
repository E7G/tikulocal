package com.e7g.tikulocal;
import android.app.NativeActivity;
import android.content.ClipData;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.widget.Toast;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
public class TikuActivity extends NativeActivity {
    private static final int PICK = 9011, SAVE = 9012;
    private static final long MAX_BYTES = 128L * 1024 * 1024;
    public boolean prefersDark() {
        int mode=getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK;
        return mode==android.content.res.Configuration.UI_MODE_NIGHT_YES;
    }
    public void openDocuments() {
        runOnUiThread(() -> {
            Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.setType("*/*");
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true);
            intent.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{
                "application/json",
                "application/zip",
                "application/x-zip-compressed",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/octet-stream"
            });
            startActivityForResult(intent,PICK);
        });
    }
    public void exportAnswers() {
        runOnUiThread(() -> {
            Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType("application/json");
            intent.putExtra(Intent.EXTRA_TITLE,"tikulocal-answers.json");
            startActivityForResult(intent,SAVE);
        });
    }
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
        super.onActivityResult(requestCode,resultCode,data);
        if(resultCode!=RESULT_OK||data==null)return;
        try{
            if(requestCode==PICK){
                ClipData clips=data.getClipData();
                if(clips!=null){
                    for(int i=0;i<clips.getItemCount();i++)importOne(clips.getItemAt(i).getUri());
                } else if(data.getData()!=null)importOne(data.getData());
            } else if(requestCode==SAVE&&data.getData()!=null){
                File temp=new File(getFilesDir(),"export-pending.json");
                if(!temp.isFile())throw new IOException("Export data is missing");
                try(InputStream in=new FileInputStream(temp);
                    OutputStream out=getContentResolver().openOutputStream(data.getData(),"w")){
                    if(out==null)throw new IOException("Output stream unavailable");
                    transfer(in,out,MAX_BYTES*4);
                }
                Toast.makeText(this,"已导出 JSON 题库",Toast.LENGTH_SHORT).show();
            }
        }catch(Exception error){Toast.makeText(this,"题库文件操作失败："+error.getMessage(),Toast.LENGTH_LONG).show();}
    }
    private String displayName(Uri uri){
        try(Cursor cursor=getContentResolver().query(uri,null,null,null,null)){
            if(cursor!=null&&cursor.moveToFirst()){
                int i=cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if(i>=0)return cursor.getString(i);
            }
        }catch(Exception ignored){}
        return "import";
    }
    private void importOne(Uri uri)throws IOException{
        String name=displayName(uri).toLowerCase(java.util.Locale.ROOT);
        String ext=name.endsWith(".docx")?".docx":name.endsWith(".json")?".json":name.endsWith(".zip")?".zip":null;
        if(ext==null)throw new IOException("Only .docx, .json and .zip files are supported");
        File imports=new File(getFilesDir(),"imports");
        if(!imports.isDirectory()&&!imports.mkdirs())throw new IOException("Cannot create imports folder");
        File target=new File(imports,UUID.randomUUID().toString()+ext);
        try(InputStream in=getContentResolver().openInputStream(uri);
            OutputStream out=new FileOutputStream(target)){
            if(in==null)throw new IOException("Input stream unavailable");
            transfer(in,out,MAX_BYTES);
        }catch(IOException e){target.delete();throw e;}
        File queue=new File(getFilesDir(),"pending-imports.txt");
        try(FileOutputStream stream=new FileOutputStream(queue,true)){
            stream.write((target.getAbsolutePath()+"\n").getBytes(StandardCharsets.UTF_8));
            stream.flush();
        }
    }
    private static void transfer(InputStream in,OutputStream out,long limit)throws IOException{
        byte[] bytes=new byte[32768];long sum=0;int n;
        while((n=in.read(bytes))!=-1){
            sum+=n;if(sum>limit)throw new IOException("File is too large");
            out.write(bytes,0,n);
        }
        out.flush();
    }
}
