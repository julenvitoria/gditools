unit About;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, FileUtil, Forms, Controls, Graphics, Dialogs, ExtCtrls,
  StdCtrls;

type
  { TfrmAbout }

  TfrmAbout = class(TForm)
    btnClose: TButton;
    imgLogo: TImage;
    lblAppName: TLabel;
    lblAppInfo: TLabel;
    lblAuthors: TLabel;
    lblPoweredBy: TLabel;
    lblCredits: TLabel;
    procedure btnCloseClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
    procedure lblAuthorsClick(Sender: TObject);
    procedure lblAuthorsMouseEnter(Sender: TObject);
    procedure lblAuthorsMouseLeave(Sender: TObject);
  private
    { private declarations }
  public
    { public declarations }
  end;

var
  frmAbout: TfrmAbout;

implementation

uses
  LCLIntf, Version;

{$R *.lfm}

{ TfrmAbout }

procedure TfrmAbout.btnCloseClick(Sender: TObject);
begin
  Close;
end;

procedure TfrmAbout.FormCreate(Sender: TObject);
begin
  lblAppName.Caption := Application.Title;
  Caption := 'About ' + Application.Title + '...';
  lblAppInfo.Caption := 'Version ' + GetFileVersion + ' on ' + GetTargetInfo;
end;

procedure TfrmAbout.lblAuthorsClick(Sender: TObject);
begin
  OpenURL((Sender as TLabel).Hint);
end;

procedure TfrmAbout.lblAuthorsMouseEnter(Sender: TObject);
begin
  with (Sender as TLabel) do
  begin
    Font.Underline := True;
    Cursor := crHandPoint;
  end;
end;

procedure TfrmAbout.lblAuthorsMouseLeave(Sender: TObject);
begin
  with (Sender as TLabel) do
  begin
    Font.Underline := False;
    Cursor := crDefault;
  end;
end;

end.
